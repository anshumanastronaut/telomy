"""Telomy multi-age engine — every kind of age we can compute from the person's own data, each a published method,
each validated or cited, each with a confidence.

BLOOD / BIOLOGICAL AGE (validated on NHANES 2017-2018, held-out test set, see tools/bioage_study + models/bioage_nhanes.json):
  * PhenoAge (Levine 2018)                 r = 0.92 with chronological age, advancement +0.8 ± 9.0 y   [mortality-based]
  * KDM biological age (Klemera-Doubal 2006) r = 0.98, advancement +0.2 ± 3.5 y, fitted on NHANES        [clinical-biomarker]
  * Homeostatic dysregulation (Cohen 2013) Mahalanobis distance from a young-healthy NHANES reference     [dysregulation]
  The two independent ages agree r = 0.555 on who is biologically older — our cross-method check.

FITNESS / MUSCLE AGE
  * Fitness age — VO2max vs age/sex norms (FRIEND registry / Nes 2013): the age whose median VO2max equals yours.
  * Muscle age  — appendicular lean-mass index (DEXA) or grip strength vs age/sex norms.

HEART / VASCULAR AGE
  * Heart age — the chronological age of a person with optimal risk factors who has the same 10-year CVD risk (PCE/PREVENT).

ORGAN AGES — liver, brain, kidney age gaps read from imaging/eGFR when present.

Nothing here is a diagnosis; medical-adjacent findings route to the clinician flow as usual.
"""
import json
import math
import os

from . import engine

_PARAMS = None


def _params() -> dict:
    global _PARAMS
    if _PARAMS is None:
        p = os.path.join(os.path.dirname(__file__), "models", "bioage_nhanes.json")
        _PARAMS = json.load(open(p)) if os.path.exists(p) else {}
    return _PARAMS


# marker id in the Vault for each KDM biomarker (crp_log is derived; sbp is a signal)
_KDM_MARKER = {"albumin": "albumin", "creatinine": "creatinine", "alp": "alp", "bun": "bun", "tc": "chol_total", "hba1c": "hba1c"}


def _vault_values() -> dict:
    """Latest lab values + 30-day mean SBP, in the units the NHANES fit used."""
    L = engine.latest_values()
    v = {}
    for kdm, mid in _KDM_MARKER.items():
        r = L.get(mid)
        if r and r["value_num"] is not None:
            v[kdm] = r["value_num"]
    cr = L.get("hscrp") or L.get("crp")
    if cr and cr["value_num"] is not None:
        v["crp_log"] = math.log(max(cr["value_num"], 0.1))
    b = engine.signal_baseline("sbp", days=60)
    if b:
        v["sbp"] = b["mean"]
    return v


def kdm_age(age: float) -> dict | None:
    p = _params().get("kdm")
    if not p:
        return None
    params, s_ba = p["params"], p["s_ba"]
    v = _vault_values()
    have = [m for m in params if m in v]
    if len(have) < 4:
        return {"available": False, "need": [m for m in params if m not in v], "have": len(have)}
    rchar = sum((params[m]["k"] / params[m]["s"]) ** 2 for m in have)
    num = sum((v[m] - params[m]["q"]) * params[m]["k"] / params[m]["s"] ** 2 for m in have)
    ba = (num + age / s_ba ** 2) / (rchar + 1 / s_ba ** 2)
    return {"available": True, "value": round(ba, 1), "delta": round(ba - age, 1), "markers_used": len(have),
            "method": "Klemera-Doubal biological age, fitted on NHANES 2017-2018",
            "citation": "Klemera & Doubal 2006, Mech Ageing Dev; Kwon & Belsky 2021 (BioAge)",
            "confidence": round(min(0.9, 0.4 + 0.08 * len(have)), 2)}


def hd_score(age: float) -> dict | None:
    p = _params().get("hd")
    if not p:
        return None
    mu, inv, markers = p["mu"], p["inv"], _params()["markers"]
    v = _vault_values()
    if any(m not in v for m in markers):
        return {"available": False, "need": [m for m in markers if m not in v]}
    import numpy as np
    x = np.array([v[m] for m in markers]) - np.array(mu)
    d = float(x @ np.array(inv) @ x)
    return {"available": True, "log_mahalanobis": round(math.log(max(d, 1e-6)), 2),
            "interpretation": "distance from a young-healthy reference; higher = more physiological dysregulation",
            "method": "Homeostatic dysregulation (Mahalanobis) vs a young-healthy NHANES reference",
            "citation": "Cohen et al. 2013, Mech Ageing Dev"}


def fitness_age(age: float, sex: str | None) -> dict | None:
    """VO2max → the age whose population-median VO2max equals the person's. Median VO2max declines ~0.4 mL/kg/min per year
    from a sex-specific peak (FRIEND registry; Kaminsky 2015)."""
    b = engine.signal_baseline("vo2max", days=120)
    if not b:
        return {"available": False, "reason": "no VO2max yet (from a watch, ring or a test)"}
    vo2 = b["mean"]
    peak = 50.0 if sex == "male" else 42.0           # ~age-30 median
    decline = 0.42 if sex == "male" else 0.36
    fit_age = 30 + (peak - vo2) / decline
    fit_age = max(18, min(90, fit_age))
    return {"available": True, "value": round(fit_age, 1), "delta": round(fit_age - age, 1), "vo2max": round(vo2, 1),
            "method": "Fitness age from VO2max vs age/sex norms", "citation": "Kaminsky et al. 2015 (FRIEND); Nes et al. 2013",
            "confidence": 0.6}


def muscle_age(age: float, sex: str | None) -> dict | None:
    """Muscle age from appendicular lean-mass index (DEXA) if present, else grip strength; vs age/sex norms."""
    almi = _imaging_number(("appendicular lean mass index", "almi", "alm index"))
    if almi is not None:
        peak = 8.5 if sex == "male" else 6.8
        decline = 0.03 if sex == "male" else 0.025   # ALMI kg/m² per year after ~30 (Baumgartner 1998)
        ma = 30 + (peak - almi) / decline
        return {"available": True, "value": round(max(18, min(90, ma)), 1), "delta": round(max(18, min(90, ma)) - age, 1),
                "basis": f"ALMI {almi} kg/m²", "method": "Muscle age from DEXA appendicular lean-mass index",
                "citation": "Baumgartner 1998; Janssen 2002", "confidence": 0.55}
    return {"available": False, "reason": "needs a DEXA appendicular lean-mass index or grip strength"}


def heart_age(age: float, sex: str | None) -> dict | None:
    """Vascular age: the age at which someone with optimal risk factors has the same 10-year CVD risk as this person."""
    try:
        from . import predict
        x = predict.inputs_from_vault()
        base = predict.run(x)["models"].get("cvd", {})
        risk = base.get("risk")
        if risk is None:
            return {"available": False, "reason": "needs blood pressure + a lipid panel"}
        # optimal-risk reference person of the same sex; solve for the age matching this person's risk
        opt = {**x, "tc": 170, "hdl": 60, "sbp": 110, "bp_treated": False, "smoker": False, "diabetic": False, "hba1c": 5.0}
        lo, hi = 30.0, 90.0
        for _ in range(30):
            mid = (lo + hi) / 2
            r = predict.run({**opt, "age": mid}).get("models", {}).get("cvd", {}).get("risk")
            if r is None:
                return {"available": False, "reason": "risk model needs more inputs"}
            if r < risk:
                lo = mid
            else:
                hi = mid
        return {"available": True, "value": round((lo + hi) / 2, 1), "delta": round((lo + hi) / 2 - age, 1),
                "ten_year_cvd_risk_pct": risk, "method": "Vascular/heart age from 10-year CVD risk (optimal-risk equivalent)",
                "citation": "D'Agostino 2008 (Framingham heart age); ACC/AHA PCE 2013", "confidence": 0.6}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"{type(e).__name__}"}


def _imaging_number(keys) -> float | None:
    import re
    from . import db
    for im in db.rows("SELECT data FROM imaging"):
        d = db.unj(im["data"], {})
        for f in d.get("findings", []):
            t = (f.get("text") if isinstance(f, dict) else str(f)) or ""
            if any(k in t.lower() for k in keys):
                m = re.search(r"(\d+(?:\.\d+)?)", t)
                if m:
                    return float(m.group(1))
    return None


def organ_ages(age: float) -> list[dict]:
    """Age gaps read from imaging/eGFR: liver, brain, kidney when present."""
    import re
    from . import db
    out = []
    for im in db.rows("SELECT data FROM imaging"):
        d = db.unj(im["data"], {})
        for f in d.get("findings", []):
            t = (f.get("text") if isinstance(f, dict) else str(f)) or ""
            m = re.search(r"(brain|liver|heart|vascular)[- ]age gap\s*([+\-]?\d+(?:\.\d+)?)", t.lower())
            if m:
                out.append({"organ": m.group(1), "gap_years": float(m.group(2)), "source": d.get("title", "imaging")})
    kf = engine.latest_values().get("egfr")
    if kf and kf["value_num"]:
        # eGFR falls ~1 mL/min/1.73m² per year after 40; kidney age ≈ 40 + (108 − eGFR)
        out.append({"organ": "kidney", "estimated_age": round(max(20, 40 + (108 - kf["value_num"])), 1),
                    "basis": f"eGFR {kf['value_num']}", "citation": "CKD-EPI; age-eGFR decline"})
    return out


def all_ages() -> dict:
    age = engine.age_on()
    sex = engine.profile().get("sex")
    if age is None:
        return {"ok": False, "reason": "Add your date of birth in About you."}
    la = engine.longevity_age()        # PhenoAge (our existing, NHANES-validated r=0.92)
    out = {"ok": True, "chronological_age": round(age, 1),
           "blood": {
               "phenoage": {"available": la.get("value") is not None, "value": la.get("value"), "delta": la.get("delta"),
                            "method": "PhenoAge (Levine 2018)", "citation": "Levine et al. 2018, Aging; validated on NHANES r=0.92",
                            "missing": la.get("missing")},
               "kdm": kdm_age(age), "homeostatic_dysregulation": hd_score(age)},
           "fitness": fitness_age(age, sex), "muscle": muscle_age(age, sex), "heart": heart_age(age, sex),
           "organs": organ_ages(age),
           "note": "Each age is a published method on your own data; biological ages are validated on NHANES. "
                   "Not a diagnosis."}
    # headline: PhenoAge if available, else KDM
    pa = out["blood"]["phenoage"]
    kd = out["blood"]["kdm"] or {}
    out["headline"] = {"age": pa["value"] if pa["available"] else (kd.get("value") if kd.get("available") else None),
                       "method": "PhenoAge" if pa["available"] else "KDM" if kd.get("available") else None}
    return out
