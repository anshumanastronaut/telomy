"""Telomy-LLX unified report analysis — one panel in, the whole grounded picture out.

analyze_report(panel) orchestrates every trained model as a grounded tool and composes a single
explanation:
  • blood age (clock)            • biological age + acceleration (PhenoAge)
  • muscular age (if body-composition / anthropometry present)
  • disease screen (ranked conditions)   • 10-year mortality risk
Every number is a tool result with provenance; Telomy-LLX narrates, it never invents.

Run `python -m telomy_llx.report` for a demo on a full report.
"""
from __future__ import annotations
import json, os
import numpy as np, joblib
from . import tools, disease_tools

MUSCLE_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "muscle")
MUSCLE_FEATS = {
    "muscle_dxa": ["sex", "almi", "alm_kg", "total_lean_kg", "trunk_lean_kg", "total_fat_pct",
                   "total_fat_kg", "lean_fat_ratio", "bmd_total", "bmd_lumbar", "bmi", "waist",
                   "arm_circ", "weight", "height"],
    "muscle_anthro": ["sex", "bmi", "waist", "arm_circ", "leg_len", "arm_len", "weight", "height"],
}
_MM = json.load(open(os.path.join(MUSCLE_ASSETS, "muscle_metrics.json")))
_CACHE = {}

def _muscle_model(name):
    if name not in _CACHE:
        _CACHE[name] = joblib.load(os.path.join(MUSCLE_ASSETS, f"{name}.joblib"))
    return _CACHE[name]

def _has(panel, feats, k):
    return sum(1 for f in feats if panel.get(f) not in (None, "")) >= k

def muscular_age(panel: dict):
    """Pick the richest muscle model the inputs support; return muscular age + acceleration."""
    if _has(panel, [f for f in MUSCLE_FEATS["muscle_dxa"] if f not in ("sex",)], 4):
        name = "muscle_dxa"
    elif _has(panel, ["bmi", "waist", "arm_circ", "weight", "height"], 3):
        name = "muscle_anthro"
    else:
        return None
    feats = MUSCLE_FEATS[name]
    x = np.array([[float(panel[f]) if panel.get(f) not in (None, "") else np.nan for f in feats]])
    pred = float(_muscle_model(name).predict(x)[0])
    r = {"tool": "muscular_age", "model": name, "muscular_age_years": round(pred, 1),
         "model_test_MAE": _MM.get(name, {}).get("test_MAE_years")}
    if panel.get("age"):
        r["muscular_age_acceleration_years"] = round(pred - float(panel["age"]), 1)
    return r

def analyze_report(panel: dict) -> dict:
    """One blood/clinical panel -> the full grounded Telomy picture."""
    out = {"inputs_provided": sorted(k for k in panel if panel.get(k) not in (None, ""))}
    out["blood_age"] = tools.predict_age(panel)
    pa = tools.phenoage(panel)
    if "error" not in pa:
        out["biological_age"] = pa
    out["age_drivers"] = tools.explain_drivers(panel)
    m = muscular_age(panel)
    if m:
        out["muscular_age"] = m
    out["disease_screen"] = disease_tools.predict_diseases(panel, topk=5)
    out["mortality_10y"] = disease_tools.mortality_risk_10y(panel)
    out["summary"] = _compose(panel, out)
    out["disclaimer"] = ("Screening & risk estimates from routine measurements, grounded in trained "
                         "models — not a diagnosis. Review abnormal results with a clinician. Data "
                         "stays on device.")
    return out

def _compose(panel, out) -> str:
    L = []
    ba = out.get("blood_age", {})
    if ba.get("predicted_age_years") is not None:
        extra = f" (calendar age {int(panel['age'])})" if panel.get("age") else ""
        L.append(f"Blood age ≈ {ba['predicted_age_years']:.0f}{extra}, ±{ba.get('typical_error_years',9):.0f}y.")
    bio = out.get("biological_age", {})
    if bio.get("age_acceleration_years") is not None:
        a = bio["age_acceleration_years"]
        L.append(f"Biologically {abs(a):.0f}y {'older' if a>0 else 'younger'} than calendar age (PhenoAge {bio['phenoage_years']:.0f}).")
    mus = out.get("muscular_age", {})
    if mus.get("muscular_age_acceleration_years") is not None:
        a = mus["muscular_age_acceleration_years"]
        L.append(f"Muscle/body composition reads {abs(a):.0f}y {'older' if a>0 else 'younger'}.")
    top = [d for d in out.get("disease_screen", {}).get("ranked", []) if d["probability"] >= 0.5]
    if top:
        L.append("Worth a clinician's look: " + ", ".join(f"{d['condition'].replace('_',' ')} ({d['probability']:.0%})" for d in top[:3]) + ".")
    mr = out.get("mortality_10y", {})
    if mr.get("risk_10y") is not None:
        L.append(f"Modelled 10-year mortality risk {mr['risk_10y']:.0%} (population ranking, not a prognosis).")
    return " ".join(L)

if __name__ == "__main__":
    report = {"age": 58, "sex": 1, "albumin": 4.0, "creatinine": 1.3, "glucose": 141, "crp_mgL": 5.5,
              "lymph_pct": 24, "neut_pct": 65, "mono_pct": 8, "eos_pct": 2, "baso_pct": 1, "rbc": 4.8,
              "hgb": 14.5, "hct": 44, "mcv": 93, "rdw": 14.3, "platelets": 240, "mpv": 10.4, "wbc": 8.1,
              "alt": 42, "ast": 40, "alp": 98, "ggt": 65, "bun": 20, "uric_acid": 7.2, "calcium": 9.4,
              "phosphorus": 3.5, "sodium": 140, "potassium": 4.3, "bicarb": 25, "bilirubin": 0.8,
              "total_protein": 7.1, "globulin": 3.1, "iron": 85, "hba1c": 6.5, "total_chol": 215,
              "hdl": 36, "trig": 200,
              # body composition (optional -> enables muscular age)
              "almi": 7.2, "alm_kg": 22.0, "total_lean_kg": 52, "total_fat_pct": 30, "bmi": 28,
              "waist": 104, "weight": 85, "height": 174}
    r = analyze_report(report)
    print("SUMMARY:\n ", r["summary"], "\n")
    print(json.dumps({k: v for k, v in r.items() if k in
          ("blood_age", "biological_age", "muscular_age", "mortality_10y")}, indent=2))
    print("TOP DISEASE SIGNALS:", [(d["condition"], d["probability"]) for d in r["disease_screen"]["ranked"]])
