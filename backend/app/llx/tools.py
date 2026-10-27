"""Telomy-LLX grounded tool layer.

The SLM is NOT allowed to guess ages or biomarker interpretations from text. Instead it emits a
tool call, this layer runs the *trained* NHANES clocks (research/ageclock) and the published
PhenoAge formula, and the SLM then explains the returned numbers. Every quantitative statement the
model makes is therefore a tool result with provenance — the structural fix for medical-LLM
hallucination.

Run `python -m telomy_llx.tools` for a live demo.
"""
from __future__ import annotations
import json, os, math
import numpy as np
import joblib

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "clocks")

# feature order MUST match research/ageclock/train.py exactly (models were fit on these vectors)
FEATURE_ORDER = {
    "telomy_full": ["sex","albumin","creatinine","glucose","crp_mgL","lymph_pct","neut_pct",
        "mono_pct","eos_pct","baso_pct","rbc","hgb","hct","mcv","rdw","platelets","mpv","wbc",
        "alt","ast","alp","ggt","bun","uric_acid","calcium","phosphorus","sodium","potassium",
        "bicarb","bilirubin","total_protein","globulin","iron","hba1c","total_chol","hdl","trig"],
    "telomy_clinic9": ["albumin","creatinine","glucose","crp_mgL","lymph_pct","mcv","rdw","alp","wbc"],
    "telomy_metabolic": ["glucose","hba1c","insulin","total_chol","hdl","trig","uric_acid","bun"],
    "telomy_liverkidney": ["alt","ast","alp","ggt","bilirubin","albumin","total_protein","globulin","creatinine","bun","uric_acid"],
    "telomy_cbc": ["wbc","lymph_pct","neut_pct","mono_pct","eos_pct","baso_pct","rbc","hgb","hct","mcv","rdw","platelets","mpv"],
}

# adult reference medians + whether HIGHER reads as OLDER (+1) or YOUNGER (-1); drives explanations
REF = {  # (median, age_direction)
    "albumin": (4.3, -1), "creatinine": (0.85, +1), "glucose": (98, +1), "crp_mgL": (1.8, +1),
    "lymph_pct": (30, -1), "mcv": (89, +1), "rdw": (12.9, +1), "alp": (67, +1), "wbc": (7.0, 0),
    "hba1c": (5.5, +1), "hdl": (53, -1), "trig": (110, +1), "uric_acid": (5.3, +1), "bun": (13, +1),
}
_METRICS = json.load(open(os.path.join(ASSETS, "clock_metrics.json")))
_CACHE: dict = {}

def _load(name):
    if name not in _CACHE:
        _CACHE[name] = joblib.load(os.path.join(ASSETS, f"{name}.joblib"))
    return _CACHE[name]

def _vec(panel, name):
    order = FEATURE_ORDER[name]
    return np.array([[float(panel[f]) if panel.get(f) not in (None, "") else np.nan for f in order]])

def _choose(panel):
    """Pick the richest clock the panel can feed (full if >=18 markers present, else clinic9)."""
    full_have = sum(1 for f in FEATURE_ORDER["telomy_full"] if panel.get(f) not in (None, ""))
    if full_have >= 18:
        return "telomy_full"
    c9_have = sum(1 for f in FEATURE_ORDER["telomy_clinic9"] if panel.get(f) not in (None, ""))
    return "telomy_clinic9" if c9_have >= 5 else "telomy_full"

# ---------------------------------------------------------------- tools
def predict_age(panel: dict) -> dict:
    """Estimate chronological age from a blood panel using the best-fitting trained clock."""
    name = _choose(panel)
    model = _load(name)
    pred = float(model.predict(_vec(panel, name))[0])
    used = [f for f in FEATURE_ORDER[name] if panel.get(f) not in (None, "")]
    mae = _METRICS.get(name, {}).get("test_MAE_years")
    return {"tool": "predict_age", "model": name, "predicted_age_years": round(pred, 1),
            "typical_error_years": mae, "markers_used": len(used),
            "markers_missing": [f for f in FEATURE_ORDER[name] if f not in used]}

def phenoage(panel: dict) -> dict:
    """Levine-2018 phenotypic (biological) age + age acceleration. Needs the 9 markers + chronological age."""
    need = ["albumin","creatinine","glucose","crp_mgL","lymph_pct","mcv","rdw","alp","wbc","age"]
    missing = [k for k in need if panel.get(k) in (None, "")]
    if missing:
        return {"tool": "phenoage", "error": "missing_inputs", "missing": missing}
    d = {k: float(panel[k]) for k in need}
    alb, creat, glu = d["albumin"]*10, d["creatinine"]*88.4, d["glucose"]*0.0555
    crp = math.log(max(d["crp_mgL"]/10.0, 0.01))
    xb = (-19.907 - 0.0336*alb + 0.0095*creat + 0.1953*glu + 0.0954*crp - 0.0120*d["lymph_pct"]
          + 0.0268*d["mcv"] + 0.3306*d["rdw"] + 0.00188*d["alp"] + 0.0554*d["wbc"] + 0.0804*d["age"])
    g = 0.0076927
    mort = 1 - math.exp(-math.exp(xb) * (math.exp(g*120) - 1) / g)
    mort = min(max(mort, 1e-6), 1-1e-6)
    pa = 141.50225 + math.log(-0.00553*math.log(1-mort)) / 0.090165
    return {"tool": "phenoage", "phenoage_years": round(pa,1), "chronological_age_years": d["age"],
            "age_acceleration_years": round(pa - d["age"], 1),
            "mortality_risk_score": round(mort, 4),
            "note": "PhenoAge is mortality-validated (Levine 2018). Positive acceleration = biologically older than calendar age."}

def explain_drivers(panel: dict) -> dict:
    """Which measured markers push the estimate older/younger vs adult reference medians."""
    older, younger, flagged = [], [], []
    for m, (med, direction) in REF.items():
        v = panel.get(m)
        if v in (None, ""):
            continue
        v = float(v); dev = (v - med) / med
        if abs(dev) < 0.12:
            continue
        effect = direction * (1 if v > med else -1)   # +1 => older, -1 => younger
        item = {"marker": m, "value": v, "reference_median": med, "pct_vs_median": round(dev*100)}
        (older if effect > 0 else younger if effect < 0 else flagged).append(item)
    return {"tool": "explain_drivers", "pushing_older": older, "pushing_younger": younger,
            "notable_but_neutral": flagged}

# ---------------------------------------------------------------- function-calling registry
TOOL_SPECS = [
    {"type": "function", "function": {"name": "predict_age",
        "description": "Estimate chronological age (years) from a routine blood panel using Telomy's trained clock. Always call this instead of guessing an age.",
        "parameters": {"type": "object", "properties": {"panel": {"type": "object",
            "description": "Blood markers by name, e.g. {albumin, creatinine, glucose, crp_mgL, mcv, rdw, alp, wbc, hba1c, hdl, trig, ...}. sex: 1=male,2=female."}}, "required": ["panel"]}}},
    {"type": "function", "function": {"name": "phenoage",
        "description": "Compute mortality-validated biological age (Levine PhenoAge) and age acceleration. Needs albumin, creatinine, glucose, crp_mgL, lymph_pct, mcv, rdw, alp, wbc AND chronological age.",
        "parameters": {"type": "object", "properties": {"panel": {"type": "object"}}, "required": ["panel"]}}},
    {"type": "function", "function": {"name": "explain_drivers",
        "description": "List which markers read older/younger vs adult reference medians, to explain a result.",
        "parameters": {"type": "object", "properties": {"panel": {"type": "object"}}, "required": ["panel"]}}},
]
_DISPATCH = {"predict_age": predict_age, "phenoage": phenoage, "explain_drivers": explain_drivers}

def call(name: str, args: dict) -> dict:
    if name not in _DISPATCH:
        return {"error": f"unknown tool {name}"}
    return _DISPATCH[name](args.get("panel", args))

if __name__ == "__main__":
    demo = {"age": 52, "sex": 1, "albumin": 4.1, "creatinine": 1.3, "glucose": 142, "crp_mgL": 6.2,
            "lymph_pct": 24, "neut_pct": 64, "mono_pct": 8, "eos_pct": 3, "baso_pct": 1,
            "rbc": 4.9, "hgb": 15.1, "hct": 45, "mcv": 94, "rdw": 14.1, "platelets": 240, "mpv": 10.5,
            "wbc": 8.2, "alt": 44, "ast": 38, "alp": 95, "ggt": 60, "bun": 18, "uric_acid": 7.1,
            "calcium": 9.4, "phosphorus": 3.5, "sodium": 140, "potassium": 4.2, "bicarb": 25,
            "bilirubin": 0.8, "total_protein": 7.1, "globulin": 3.0, "iron": 90, "hba1c": 6.4,
            "total_chol": 212, "hdl": 38, "trig": 190}
    print("predict_age  :", json.dumps(call("predict_age", {"panel": demo}), indent=2))
    print("phenoage     :", json.dumps(call("phenoage", {"panel": demo}), indent=2))
    print("explain      :", json.dumps(call("explain_drivers", {"panel": demo}), indent=2))
