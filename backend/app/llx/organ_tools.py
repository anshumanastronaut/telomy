"""Telomy-LLX organ-specific aging clocks (NHANES 49.7k).

Per-organ age from routine blood chemistry: metabolic, hepatic, renal, immune, cardiometabolic. Each model
predicts chronological age from that organ's markers; the residual (organ age − your real age) is the
**age acceleration** — the signal (which system is older/younger than your birthday). Blood-chemistry grade
(MAE 11–14 y), so a RELATIVE / trajectory signal, not a precise single number. Decision-support.
"""
from __future__ import annotations
import json
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
            # fall back: the per-organ feature lists ship here if the research json isn't present
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


def _calibration() -> dict:
    """Per-organ age-bias correction (research/ageclock/calibrate_organ_clocks.py). The age-prediction models
    regress toward the population mean (over-age the young, under-age the old); this linear correction removes
    that age-dependent bias so age_acceleration is meaningful at any age. Empty dict if the file is absent."""
    global _CALIB
    if _CALIB is None:
        import json
        p = os.path.join(ASSETS, "organ_calibration.json")
        try:
            _CALIB = json.load(open(p)) if os.path.exists(p) else {}
        except Exception:  # noqa: BLE001
            _CALIB = {}
    return _CALIB


def organ_ages(panel: dict, chronological_age: float | None = None) -> dict:
    """Return per-organ age + age-acceleration from a blood panel. `sex`: 1 male / 2 female."""
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
            pred = pred - (cal["a"] + cal["b"] * age)
        accel = round(pred - age, 1) if age else None
        out.append({"organ": organ, "label": LABEL[organ], "organ_age": round(pred, 1),
                    "age_acceleration_years": accel,
                    "status": ("older" if accel and accel > 2 else "younger" if accel and accel < -2 else "on_track") if accel is not None else None})
    out.sort(key=lambda r: -(r["age_acceleration_years"] or 0))
    return {"chronological_age": age, "organs": out,
            "note": "Per-organ age from routine blood chemistry (NHANES 49.7k). Relative signal — which system "
                    "is aging faster — not a precise number. Proteomics/imaging would tighten each clock.",
            "source": "Telomy organ clocks (mirrors Cell 2026 Digital Aging Twin)"}


def call(name, args):
    return {"organ_ages": organ_ages}[name](**args)
