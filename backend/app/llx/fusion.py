"""Wearable-fusion risk engine — Telomy's differentiator.

Joins the device-derived cardiovascular signals we already collect (resting HR, HRV = RMSSD/SDNN,
nocturnal SpO2) to the blood-based models (aging clocks, PhenoAge, disease screen, 10-yr mortality).

Honesty: we do NOT have a labelled continuous-wearable outcome cohort, so the wearable contribution is
NOT a trained model — it is a transparent, literature-anchored risk overlay (published hazard ratios,
cited below). The blood/disease numbers remain the trained-model outputs. We combine them into one
"Telomy Risk Profile" and say plainly which part is model vs evidence-rule. This is defensible and
upgradeable: when the Telomy device cohort has outcomes, the overlay is replaced by a trained fusion head.

Evidence anchors (population hazard ratios, all-cause/CVD mortality):
  • Resting HR: ~+1.09 CVD / +1.17 all-cause mortality per +10 bpm; RHR>80 elevated.  (Zhang 2016 CMAJ;
    Jensen 2013).
  • HRV SDNN: low SDNN (<50 ms) ~1.3–1.4x risk; <100 ms "compromised".  (Dekker 2000 Circulation).
  • RMSSD: low parasympathetic tone tracks SDNN risk.
  • Nocturnal SpO2: mean <90% or min <88% = clinically significant hypoxemia; raises CV/mortality risk.
"""
from __future__ import annotations
from . import report as _report

# qualitative bands (value -> (flag, weight)); weight feeds a transparent 0..1 wearable-risk index
def _resting_hr_band(hr):
    if hr is None: return None
    if hr >= 90: return ("high resting HR (≥90)", 0.9)
    if hr >= 80: return ("elevated resting HR (80–89)", 0.6)
    if hr >= 70: return ("upper-normal resting HR (70–79)", 0.3)
    return ("healthy resting HR (<70)", 0.0)

def _sdnn_band(sdnn):
    if sdnn is None: return None
    if sdnn < 20: return ("very low HRV/SDNN (<20 ms)", 1.0)
    if sdnn < 50: return ("low HRV/SDNN (20–50 ms)", 0.7)
    if sdnn < 100: return ("compromised HRV/SDNN (50–100 ms)", 0.3)
    return ("healthy HRV/SDNN (≥100 ms)", 0.0)

def _spo2_band(mean_spo2, min_spo2):
    if mean_spo2 is None and min_spo2 is None: return None
    if (min_spo2 is not None and min_spo2 < 88) or (mean_spo2 is not None and mean_spo2 < 90):
        return ("significant nocturnal desaturation", 1.0)
    if (min_spo2 is not None and min_spo2 < 92) or (mean_spo2 is not None and mean_spo2 < 94):
        return ("mild nocturnal desaturation", 0.5)
    return ("normal nocturnal SpO₂", 0.0)

def _hr_recovery_band(hrr):
    # 1-min post-exercise HR drop: <=12 abnormal (~2x mortality, Cole NEJM), 13-24 ok, >=25 excellent
    if hrr is None: return None
    if hrr <= 12: return ("abnormal heart-rate recovery (≤12 bpm)", 1.0)
    if hrr < 25: return ("fair heart-rate recovery (13–24 bpm)", 0.4)
    return ("strong heart-rate recovery (≥25 bpm)", 0.0)

def _vo2max_band(vo2, age, sex):
    # cardiorespiratory fitness — the strongest modifiable mortality signal. Rough age/sex percentile cut.
    if vo2 is None or age is None: return None
    poor = 30 if (sex == 1) else 25            # ml/kg/min, coarse "low fitness" threshold ~midlife
    good = 42 if (sex == 1) else 35
    if vo2 < poor: return (f"low cardiorespiratory fitness (VO₂max {vo2})", 1.0)
    if vo2 < good: return (f"moderate fitness (VO₂max {vo2})", 0.4)
    return (f"high fitness (VO₂max {vo2})", 0.0)

def baseline_rhr_signal(current, baseline, sd=None):
    """Personal-baseline (n-of-1) RHR deviation — Johnson's actual logic. Flags illness/overtraining or a
    good-recovery night relative to YOUR baseline, which the literature rates above a single population cutoff."""
    if current is None or baseline is None: return None
    delta = current - baseline
    z = (delta / sd) if sd else None
    if delta >= 7 or (z is not None and z >= 2):
        return {"delta_bpm": round(delta, 1), "z": round(z, 1) if z else None,
                "flag": "resting HR well above your baseline — possible illness, poor recovery, or late meal/alcohol", "weight": 0.8}
    if delta <= -3:
        return {"delta_bpm": round(delta, 1), "flag": "resting HR below your baseline — good recovery", "weight": 0.0}
    return {"delta_bpm": round(delta, 1), "flag": "resting HR near your baseline", "weight": 0.1}

def wearable_overlay(wearable: dict) -> dict:
    """Transparent, cited cardiovascular overlay from device signals. Prefers nocturnal RHR; weights RHR,
    fitness (VO₂max) and HR-recovery for hard-outcome risk; HRV is CONTEXT/TREND only (consumer-PPG HRV
    has no mortality cohort and MR suggests it is not causal — so it does not drive the risk tier)."""
    rhr = wearable.get("nocturnal_rhr", wearable.get("resting_hr"))   # nocturnal RHR preferred when present
    bands = {"resting_hr": _resting_hr_band(rhr),
             "vo2max": _vo2max_band(wearable.get("vo2max"), wearable.get("age"), wearable.get("sex")),
             "hr_recovery": _hr_recovery_band(wearable.get("hr_recovery_1min")),
             "spo2": _spo2_band(wearable.get("spo2_mean"), wearable.get("spo2_min"))}
    present = [b for b in bands.values() if b]
    index = round(sum(w for _, w in present) / len(present), 2) if present else None
    tier = "elevated" if index is not None and index >= 0.66 else "moderate" if index is not None and index >= 0.33 else ("low" if index is not None else None)
    out = {"flags": [f for f, _ in present], "wearable_risk_index": index, "wearable_risk_tier": tier,
           "signals_used": [k for k, v in bands.items() if v],
           "basis": "literature hazard ratios (RHR: Zhang 2016, +~10% mortality per +10 bpm; VO₂max: large "
                    "fitness-mortality cohorts; HR-recovery: Cole NEJM) — evidence overlay, not a trained model"}
    # personal-baseline RHR (n-of-1) + HRV as context, both reported but HRV does NOT drive the tier
    bl = baseline_rhr_signal(rhr, wearable.get("baseline_rhr"), wearable.get("baseline_rhr_sd"))
    if bl: out["baseline_rhr"] = bl
    sdnn = _sdnn_band(wearable.get("sdnn"))
    if sdnn: out["hrv_context"] = {"note": sdnn[0], "caveat": "HRV used for trend/recovery only — not a mortality claim on consumer PPG"}
    return out

def risk_profile(blood_panel: dict, wearable: dict | None = None) -> dict:
    """The Telomy Risk Profile: trained blood/disease models + a cited wearable overlay, fused."""
    base = _report.analyze_report(blood_panel)
    out = {"blood_models": {k: base[k] for k in
                ("blood_age", "biological_age", "muscular_age", "disease_screen", "mortality_10y") if k in base}}
    if wearable:
        ov = wearable_overlay(wearable)
        out["wearable_overlay"] = ov
    out["summary"] = _fuse_summary(base, out.get("wearable_overlay"))
    out["disclaimer"] = ("Blood/disease figures are trained-model outputs; the wearable tier is a cited "
                         "evidence overlay. Screening & population risk, not a diagnosis — review abnormal "
                         "results with a clinician. Data stays on device.")
    return out

def _fuse_summary(base, ov) -> str:
    parts = [base.get("summary", "")]
    if ov and ov.get("wearable_risk_tier"):
        fl = "; ".join(ov["flags"])
        parts.append(f"Wearable cardiovascular signals: {ov['wearable_risk_tier'].upper()} tier ({fl}).")
        # escalate the shared message when BOTH blood biological-age and wearables point the same way
        bio = base.get("biological_age", {}).get("age_acceleration_years")
        if ov["wearable_risk_tier"] == "elevated" and bio and bio > 3:
            parts.append("Blood biological age AND wearable signals both point to elevated cardiovascular "
                         "risk — this convergence is worth a clinical review and a repeat panel.")
    return " ".join(p for p in parts if p)

if __name__ == "__main__":
    import json
    panel = {"age": 58, "sex": 1, "albumin": 4.0, "creatinine": 1.3, "glucose": 141, "crp_mgL": 5.5,
             "lymph_pct": 24, "mcv": 93, "rdw": 14.3, "wbc": 8.1, "alp": 98, "hba1c": 6.5, "hdl": 36,
             "trig": 200, "ast": 40, "alt": 42, "ggt": 65, "bun": 20, "uric_acid": 7.2, "hgb": 14.5,
             "platelets": 240, "total_chol": 215}
    wearable = {"nocturnal_rhr": 84, "baseline_rhr": 72, "baseline_rhr_sd": 4, "vo2max": 31,
                "hr_recovery_1min": 11, "sdnn": 38, "spo2_mean": 92, "spo2_min": 86, "age": 58, "sex": 1}
    r = risk_profile(panel, wearable)
    print("SUMMARY:\n ", r["summary"], "\n")
    print(json.dumps(r.get("wearable_overlay"), indent=2))
