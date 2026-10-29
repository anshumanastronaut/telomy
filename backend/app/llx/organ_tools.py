"""Telomy-LLX organ-specific aging clocks (NHANES 49.7k + Linked Mortality Files).

Two views per organ system (metabolic, hepatic, renal, immune, cardiometabolic):

1. CHRONOLOGICAL organ age — a gradient-boosting model predicts chronological age from that organ's
   routine-chemistry markers; the residual (organ age − your real age) is the **age acceleration**,
   the relative signal of which system is older/younger than your birthday. Blood-chemistry grade
   (MAE 11–14 y) — a RELATIVE / trajectory signal, not a precise single number.

2. MORTALITY-ANCHORED biological organ age — the clinical PhenoAge method (Levine 2018 / Liu 2018):
   a Gompertz proportional-hazards all-cause-mortality model on that organ's markers + chronological
   age, mapped to an age scale, plus a Klemera–Doubal (2006) KDM estimator as a second opinion. This
   view is validated by its mortality discrimination (Cox HR per +1 SD acceleration), not by age MAE.

Precedents: Oh 2023 Nature (organ-specific proteomic aging), Tian 2023 Nat Med (multi-organ clinical
biological age), Nie 2022 Cell Reports (multi-omics organ ages). Decision-support, not diagnostic.

NOTE on honesty: PhenoAge takes chronological age as a model input, so its correlation with
chronological age is inflated and is never reported as standalone clock accuracy. The accuracy claim
stays the chronological-clock MAE; PhenoAge's worth is hazard discrimination.
"""
from __future__ import annotations
import json
import math
import os

import joblib
import numpy as np

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
_META = {}
_CACHE: dict = {}


def _meta():
    global _META
    if not _META:
        try:
            _META = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "research", "ageclock", "organ_results.json")))
        except Exception:  # noqa: BLE001
            _META = {}
    return _META


def available() -> bool:
    return any(os.path.exists(os.path.join(ASSETS, f"organ_{o}.joblib")) for o in ORGANS)


# per-organ feature order (must match training; sex first). Kept here so serving doesn't depend on the research tree.
ORGANS = {
    "metabolic": ["sex", "glucose_fasting", "hba1c", "insulin", "trig", "trig_serum", "hdl", "total_chol", "ldl", "uric_acid", "glucose_serum"],
    "hepatic":   ["sex", "albumin", "alt", "ast", "alp", "ggt", "bilirubin", "total_protein", "globulin"],
    "renal":     ["sex", "creatinine", "bun", "uric_acid", "phosphorus", "potassium", "sodium", "chloride", "bicarb", "calcium"],
    "immune":    ["sex", "wbc", "lymph_pct", "neut_pct", "mono_pct", "eos_pct", "baso_pct", "rdw", "platelets", "crp_mgL"],
    "cardiometabolic": ["sex", "total_chol", "hdl", "ldl", "trig", "glucose", "hba1c", "uric_acid"],
}
LABEL = {"metabolic": "Metabolic", "hepatic": "Liver", "renal": "Kidney", "immune": "Immune/inflammatory",
         "cardiometabolic": "Cardiometabolic"}


def _model(organ):
    if organ not in _CACHE:
        _CACHE[organ] = joblib.load(os.path.join(ASSETS, f"organ_{organ}.joblib"))
    return _CACHE[organ]


_CALIB = None
_PHENO = None


def _calibration() -> dict:
    """Per-organ age-bias correction (research/ageclock/calibrate_organ_clocks.py). Removes the
    age-dependent regression-to-mean bias of the chronological clock. Prefers the monotone-spline
    grid; falls back to the legacy linear a+b*age. Empty dict if the file is absent."""
    global _CALIB
    if _CALIB is None:
        p = os.path.join(ASSETS, "organ_calibration.json")
        try:
            _CALIB = json.load(open(p)) if os.path.exists(p) else {}
        except Exception:  # noqa: BLE001
            _CALIB = {}
    return _CALIB


def _bias(cal: dict, age: float) -> float:
    """Age-dependent bias correction for the chronological clock at this age."""
    if cal.get("grid_age") and cal.get("grid_corr"):
        return float(np.interp(age, cal["grid_age"], cal["grid_corr"]))
    return cal.get("a", 0.0) + cal.get("b", 0.0) * age


def _pheno() -> dict:
    """Serving params for the mortality-anchored estimators (research/ageclock/build_organ_phenoage.py)."""
    global _PHENO
    if _PHENO is None:
        p = os.path.join(ASSETS, "organ_phenoage.json")
        try:
            _PHENO = json.load(open(p)) if os.path.exists(p) else {}
        except Exception:  # noqa: BLE001
            _PHENO = {}
    return _PHENO


def _marker_vector(panel: dict, spec: dict):
    """Build this estimator's raw marker vector + count of genuinely-present markers."""
    xs, present = [], 0
    for m in spec["markers"]:
        v = panel.get(m)
        if v is not None and np.isfinite(float(v)):
            present += 1
            x = float(v)
            if m in spec.get("log_markers", []):
                x = math.log(max(x, 1e-3))
        else:
            x = spec["median"][m]            # impute with training median (already log-space if logged)
        xs.append(x)
    return np.array(xs, float), present


def phenotypic_organ_age(panel: dict, organ: str, age: float):
    """Mortality-anchored biological organ age for one organ (PhenoAge + KDM). None if unavailable."""
    spec = _pheno().get(organ)
    if not spec or not age:
        return None
    x, present = _marker_vector(panel, spec)
    if present < spec["need"]:
        return None
    # PhenoAge (Gompertz PH mortality -> age scale)
    zs = (x - np.array(spec["marker_mean"])) / np.array(spec["marker_sd"])
    age_z = (age - spec["age_mean"]) / spec["age_sd"]
    Xs = np.concatenate([zs, [age_z]])
    g = spec["gompertz"]
    lp = g["a"] + float(Xs @ np.array(g["beta"]))
    gamma = g["gamma"] if abs(g["gamma"]) > 1e-8 else 1e-8
    H = math.exp(lp) * (math.exp(gamma * _pheno()["_meta"]["T10_months"]) - 1.0) / gamma
    M = min(max(1.0 - math.exp(-H), 1e-7), 1 - 1e-7)
    am = spec["age_map"]
    phenoage = (math.log(-math.log(1.0 - M) / am["K"]) - am["a_age"]) / am["b_age"]
    # KDM (Klemera-Doubal)
    k = spec["kdm"]
    q, kk, s, s_ba = np.array(k["q"]), np.array(k["k"]), np.array(k["s"]), k["s_ba"]
    num = float(np.sum((x - q) * (kk / s**2)) + age / s_ba**2)
    den = float(np.sum((kk / s) ** 2) + 1.0 / s_ba**2)
    kdm_age = num / den
    rec = {"phenotypic_age": round(float(phenoage), 1),
           "phenotypic_acceleration_years": round(float(phenoage - age), 1)}
    # KDM is a validation-only second estimator: its per-subject value is unstable on low-age-signal
    # panels (hepatic/metabolic), so only surface it when it lands in a plausible adult band.
    if 18.0 <= kdm_age <= 100.0:
        rec["kdm_age"] = round(float(kdm_age), 1)
        rec["kdm_acceleration_years"] = round(float(kdm_age - age), 1)
    return rec


def trained_organ_age(panel: dict, organ: str, age: float):
    """Serve a Phase-2 trained clock (lung or brain) the same way as the blood clocks. Returns an
    organ dict or None. Inputs are our catalog ids (lung: fev1_pct/fvc_pct/fev1_fvc — age-free
    body-size %predicted + raw ratio; brain: cerad_total/cerad_delayed/animal_fluency/dsst)."""
    import pandas as pd
    spec = _pheno().get(organ)
    path = os.path.join(ASSETS, f"organ_{organ}.joblib")
    if not spec or not age or not os.path.exists(path):
        return None
    feats = spec["features"]
    row = {f: (float(panel[f]) if f in panel and panel[f] is not None and np.isfinite(float(panel[f])) else np.nan)
           for f in feats}
    if any(not np.isfinite(row[f]) for f in feats if f != "sex"):   # need every marker (coarse single-panel clock)
        return None
    if organ == "brain" and not (spec["age_support"][0] <= age <= spec["age_support"][1]):
        return None                                                 # do not extrapolate the 60-80 cognitive model
    pred = float(_model(organ).predict(pd.DataFrame([row], columns=feats))[0])
    pred = pred - (spec.get("cal_a", 0.0) + spec.get("cal_b", 0.0) * age)   # age-bias correction
    accel = round(pred - age, 1)
    label = {"lung": "Lung", "brain": "Brain (cognitive)"}[organ]
    conf = ("spirometry (FEV1/FVC, NHANES)" if organ == "lung"
            else "cognitive-performance, ages 60-80 (NHANES) — low confidence")
    return {"organ": organ, "label": label, "organ_age": round(pred, 1),
            "age_acceleration_years": accel,
            "status": ("older" if accel > 2 else "younger" if accel < -2 else "on_track"),
            "source": "trained", "confidence": conf}


def organ_ages(panel: dict, chronological_age: float | None = None) -> dict:
    """Return per-organ age + age-acceleration from a blood panel. `sex`: 1 male / 2 female.

    Each organ carries the chronological-clock age/acceleration (unchanged serving contract) and,
    when the mortality-anchored params + enough markers are present, a `phenotypic_age` /
    `kdm_age` block (biological-age view)."""
    import pandas as pd
    out = []
    age = chronological_age if chronological_age is not None else panel.get("age")
    for organ, feats in ORGANS.items():
        path = os.path.join(ASSETS, f"organ_{organ}.joblib")
        if not os.path.exists(path):
            continue
        row = {f: (float(panel[f]) if f in panel and panel[f] is not None else np.nan) for f in feats}
        if sum(np.isfinite(list(row.values()))) < max(3, (len(feats) - 1) // 2):
            continue                                   # not enough of this organ's markers measured
        pred = float(_model(organ).predict(pd.DataFrame([row], columns=feats))[0])
        cal = _calibration().get(organ)
        if cal and age:                                # remove the age-dependent regression-to-mean bias
            pred = pred - _bias(cal, age)
        accel = round(pred - age, 1) if age else None
        rec = {"organ": organ, "label": LABEL[organ], "organ_age": round(pred, 1),
               "age_acceleration_years": accel,
               "status": ("older" if accel and accel > 2 else "younger" if accel and accel < -2 else "on_track") if accel is not None else None}
        pheno = phenotypic_organ_age(panel, organ, age) if age else None
        if pheno:
            rec["biological_age"] = pheno
        out.append(rec)
    out.sort(key=lambda r: -(r["age_acceleration_years"] or 0))
    return {"chronological_age": age, "organs": out,
            "note": "Chronological organ age = routine-chemistry clock (NHANES 49.7k), a relative signal "
                    "(which system ages faster), MAE 11-14y, not a precise number. biological_age = "
                    "mortality-anchored PhenoAge + KDM (validated by hazard, not age MAE). Proteomics/imaging "
                    "would tighten each clock.",
            "source": "Telomy organ clocks (Oh 2023 Nature; Tian 2023 Nat Med; Nie 2022 Cell Rep; Levine 2018; Klemera-Doubal 2006)"}


def call(name, args):
    return {"organ_ages": organ_ages}[name](**args)
