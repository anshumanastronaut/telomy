"""Telomy-LLX lab-free chronic-risk tool (BRFSS ~1.3M).

The counterpart to disease_tools.py: when a member has NO recent blood panel, screen chronic-disease risk from
the non-invasive signals Telomy already has (age, sex, BMI, smoking, activity, sleep, self-rated health, known
BP/cholesterol flags, alcohol). Grounded: the SLM calls this; it returns calibrated probabilities with provenance.

Decision-support only — BRFSS outcomes are self-reported, so these rank who needs a panel / a doctor first.
"""
from __future__ import annotations
import json
import os

import joblib
import numpy as np

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "chronic")
_META = {}
_CACHE: dict = {}


def _meta():
    global _META
    if not _META:
        try:
            _META = json.load(open(os.path.join(ASSETS, "results.json")))
        except Exception:  # noqa: BLE001
            _META = {"_meta": {"features": []}}
    return _META


def available() -> bool:
    return bool(_meta().get("_meta", {}).get("features"))


def _model(name):
    if name not in _CACHE:
        _CACHE[name] = joblib.load(os.path.join(ASSETS, f"{name}.joblib"))
    return _CACHE[name]


FEATURE_ALIASES = {                       # accept friendly keys from the app/questionnaire
    "age": ["age"], "sex": ["sex"], "bmi": ["bmi"],
    "smoker": ["smoker", "smoking"], "phys_act": ["phys_act", "active", "physical_activity"],
    "gen_health": ["gen_health", "general_health"], "ment_days": ["ment_days", "mental_health_days"],
    "phys_days": ["phys_days", "physical_health_days"], "sleep_hrs": ["sleep_hrs", "sleep_hours"],
    "hi_bp_flag": ["hi_bp_flag", "high_bp", "hypertension_known"],
    "hi_chol": ["hi_chol", "high_cholesterol_known"], "heavy_drink": ["heavy_drink", "heavy_alcohol"],
    "income": ["income"], "educ": ["educ", "education"], "race": ["race"], "has_insur": ["has_insur", "insured"],
    "state": ["state"], "marital": ["marital"], "urban": ["urban"], "fruit_lt1": ["fruit_lt1"], "veg_lt1": ["veg_lt1"],
}


def _vec(features: dict):
    import pandas as pd
    feats = _meta()["_meta"]["features"]
    row = {}
    for f in feats:
        val = np.nan
        for k in FEATURE_ALIASES.get(f, [f]):
            if k in features and features[k] is not None:
                val = float(features[k]); break
        row[f] = val
    return pd.DataFrame([row], columns=feats)   # named columns → matches the fitted model, no warning


def predict_chronic(features: dict, topk: int = 6) -> dict:
    """Rank chronic-disease risk from non-invasive features. Returns top-k {condition: probability} + provenance."""
    if not available():
        return {"error": "chronic model not installed", "ranked": []}
    x = _vec(features)
    conds = [k for k in _meta() if k != "_meta"]
    out = []
    for c in conds:
        try:
            p = float(_model(c).predict_proba(x)[0, 1])
            out.append({"condition": c, "probability": round(p, 3),
                        "test_AUC": _meta()[c].get("test_AUC"), "prevalence": _meta()[c].get("prevalence")})
        except Exception:  # noqa: BLE001
            continue
    out.sort(key=lambda r: r["probability"], reverse=True)
    return {"ranked": out[:topk], "n_features_given": int(np.isfinite(x.values).sum()),
            "source": "BRFSS 2021-2023 (~1.3M)", "note": "self-reported outcomes; risk screen, not a diagnosis"}


def call(name, args):
    return {"predict_chronic": predict_chronic}[name](**args)
