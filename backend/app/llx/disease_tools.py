"""Telomy-LLX grounded disease tools.

Same principle as the aging clocks: the SLM does not diagnose from text — it calls these functions,
which run the trained NHANES disease classifiers + the 10-year mortality model, and then explains the
returned probabilities with provenance. Decision-support only; a probability is not a diagnosis.

Run `python -m telomy_llx.disease_tools` for a demo.
"""
from __future__ import annotations
import json, os
import numpy as np, joblib

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "disease")
_DM = json.load(open(os.path.join(ASSETS, "disease_metrics.json")))
_LM = json.load(open(os.path.join(ASSETS, "longterm_metrics.json")))

FEATURES_FULL = _DM["_meta"]["features_full"]            # 49 panel markers (order matters)
GLYCEMIC = ["glucose", "glucose_fasting", "glucose_serum", "hba1c"]
FEATURES_NOGLY = [f for f in FEATURES_FULL if f not in GLYCEMIC]
# the 10y-mortality model dropped 'insulin' (all-missing in the 2009-2012 follow-up subset) -> 48 feats
MORT_FEATURES = [f for f in _LM["_meta"]["features"] if f != "insulin"]
DISEASES = _DM["_meta"]["diseases"]
_CACHE: dict = {}

def _m(name):
    if name not in _CACHE:
        _CACHE[name] = joblib.load(os.path.join(ASSETS, f"{name}.joblib"))
    return _CACHE[name]

def _vec(panel, feats):
    return np.array([[float(panel[f]) if panel.get(f) not in (None, "") else np.nan for f in feats]])

def predict_diseases(panel: dict, topk: int = 5) -> dict:
    """Rank diagnosed-condition probabilities for a blood panel. Diabetes is scored WITHOUT glucose/
    HbA1c (non-circular). Returns ranked conditions with each model's held-out test AUC for context."""
    ranked = []
    for d in DISEASES:
        feats = FEATURES_NOGLY if d == "diabetes" else FEATURES_FULL
        prob = float(_m(d).predict_proba(_vec(panel, feats))[:, 1][0])
        ranked.append({"condition": d, "probability": round(prob, 3),
                       "model_test_AUC": _DM.get(d, {}).get("test_AUC")})
    ranked.sort(key=lambda r: -r["probability"])
    return {"tool": "predict_diseases", "ranked": ranked[:topk],
            "note": "Probabilities are screening signals from routine labs, not diagnoses. "
                    "Confirm with a clinician; abnormal results warrant follow-up."}

def mortality_risk_10y(panel: dict) -> dict:
    """10-year all-cause mortality risk from the routine panel (NHANES linked-mortality model)."""
    prob = float(_m("mortality_10y").predict_proba(_vec(panel, MORT_FEATURES))[:, 1][0])
    return {"tool": "mortality_risk_10y", "risk_10y": round(prob, 3),
            "model_test_AUC": _LM.get("all_cause_10y", {}).get("test_AUC"),
            "note": "Age-dominated population risk estimate for ranking, not an individual prognosis; "
                    "needs calibration + comparison vs Pooled Cohort Equations before clinical use."}

TOOL_SPECS = [
    {"type": "function", "function": {"name": "predict_diseases",
        "description": "Screen a routine blood panel for diagnosed conditions (diabetes, hypertension, "
                       "coronary heart disease, heart failure, stroke, kidney/liver disease, cancer, COPD...). "
                       "Returns ranked probabilities. Call this instead of guessing a diagnosis.",
        "parameters": {"type": "object", "properties": {"panel": {"type": "object"}}, "required": ["panel"]}}},
    {"type": "function", "function": {"name": "mortality_risk_10y",
        "description": "Estimate 10-year all-cause mortality risk from a routine blood panel.",
        "parameters": {"type": "object", "properties": {"panel": {"type": "object"}}, "required": ["panel"]}}},
]
_DISPATCH = {"predict_diseases": predict_diseases, "mortality_risk_10y": mortality_risk_10y}

def call(name, args):
    return _DISPATCH[name](args.get("panel", args)) if name in _DISPATCH else {"error": f"unknown tool {name}"}

if __name__ == "__main__":
    demo = {"age": 61, "sex": 1, "albumin": 4.0, "creatinine": 1.4, "crp_mgL": 7.0, "lymph_pct": 22,
            "neut_pct": 68, "mcv": 92, "rdw": 15.0, "wbc": 8.5, "alt": 40, "ast": 42, "alp": 100,
            "ggt": 70, "bun": 22, "uric_acid": 7.5, "hgb": 13.5, "platelets": 230, "hdl": 34,
            "total_chol": 220, "trig": 210, "hba1c": 6.6, "glucose": 150}
    print(json.dumps(predict_diseases(demo), indent=2))
    print(json.dumps(mortality_risk_10y(demo), indent=2))
