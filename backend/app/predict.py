"""Disease prediction with published, validated risk equations.

Every model works on a plain dict of inputs so it runs for the logged-in user, a doctor's patient, or a what-if
scenario. Each result carries the equation, its citation, the inputs used, missing inputs and applicability limits.
"""
import math

# --------------------------------------------------------------------------- 10-y ASCVD (Pooled Cohort Equations, 2013)
# Goff DC et al. 2013 ACC/AHA Guideline on the Assessment of Cardiovascular Risk. Circulation 2014;129:S49-73.
# White / other equations (used for South Asian users, who are known to be under-estimated; flagged in caveats).
PCE = {
    "male": {"ln_age": 12.344, "ln_tc": 11.853, "ln_age_tc": -2.664, "ln_hdl": -7.990, "ln_age_hdl": 1.769,
             "ln_sbp_t": 1.797, "ln_sbp_u": 1.764, "smoker": 7.837, "ln_age_smoker": -1.795, "dm": 0.658,
             "s0": 0.9144, "mean": 61.18},
    "female": {"ln_age": -29.799, "ln_age2": 4.884, "ln_tc": 13.540, "ln_age_tc": -3.114, "ln_hdl": -13.578,
               "ln_age_hdl": 3.149, "ln_sbp_t": 2.019, "ln_sbp_u": 1.957, "smoker": 7.574, "ln_age_smoker": -1.665,
               "dm": 0.661, "s0": 0.9665, "mean": -29.18},
}


def ascvd_pce(age, sex, tc, hdl, sbp, bp_treated=False, smoker=False, diabetic=False) -> dict:
    need = {"age": age, "total cholesterol": tc, "HDL": hdl, "systolic BP": sbp}
    missing = [k for k, v in need.items() if v is None]
    base = {"model": "Pooled Cohort Equations (ACC/AHA 2013)", "outcome": "10-year risk of heart attack or stroke",
            "citation": "Goff DC et al. Circulation 2014;129(25 Suppl 2):S49-S73."}
    if missing:
        return {**base, "risk": None, "missing": missing}
    if not 40 <= age <= 79:
        return {**base, "risk": None, "missing": [], "note": "Validated for ages 40–79; shown as a projection at age 40.",
                **_pce_value(40, sex, tc, hdl, sbp, bp_treated, smoker, diabetic)}
    return {**base, "missing": [], **_pce_value(age, sex, tc, hdl, sbp, bp_treated, smoker, diabetic)}


def _pce_value(age, sex, tc, hdl, sbp, bp_treated, smoker, diabetic):
    c = PCE["female" if sex == "female" else "male"]
    la, ltc, lh, ls = math.log(age), math.log(tc), math.log(hdl), math.log(sbp)
    s = c["ln_age"] * la + c.get("ln_age2", 0) * la * la + c["ln_tc"] * ltc + c["ln_age_tc"] * la * ltc
    s += c["ln_hdl"] * lh + c["ln_age_hdl"] * la * lh
    s += (c["ln_sbp_t"] if bp_treated else c["ln_sbp_u"]) * ls
    s += (c["smoker"] + c["ln_age_smoker"] * la) * (1 if smoker else 0) + c["dm"] * (1 if diabetic else 0)
    risk = 1 - c["s0"] ** math.exp(s - c["mean"])
    band = "low (< 5%)" if risk < 0.05 else "borderline (5–7.5%)" if risk < 0.075 else "intermediate (7.5–20%)" if risk < 0.2 else "high (≥ 20%)"
    return {"risk": round(risk * 100, 1), "band": band}


# --------------------------------------------------------------------------- Type 2 diabetes
# ADA Diabetes Risk Test (Bang H et al. Ann Intern Med 2009;151:775-783) + HbA1c bands for 5-year incidence
# (Zhang X et al. Diabetes Care 2010;33:1665-1673: A1c 5.5–6.0% → 9–25%, 6.0–6.5% → 25–50% over 5 y).
def diabetes(age, sex, bmi, hba1c, glucose, family_history=False, hypertension=False, active=True, gestational=False) -> dict:
    base = {"model": "ADA risk score + HbA1c incidence bands", "outcome": "5-year risk of type 2 diabetes",
            "citation": "Bang H et al. Ann Intern Med 2009;151:775-83; Zhang X et al. Diabetes Care 2010;33:1665-73."}
    if hba1c is not None and hba1c >= 6.5 or glucose is not None and glucose >= 126:
        return {**base, "risk": None, "band": "diabetes range — confirm with your clinician", "missing": [], "already": True}
    pts = (0 if age is None or age < 40 else 1 if age < 50 else 2 if age < 60 else 3) + (1 if sex == "male" else 0)
    pts += (1 if family_history else 0) + (1 if hypertension else 0) + (0 if active else 1) + (1 if gestational else 0)
    pts += 0 if not bmi or bmi < 25 else 1 if bmi < 30 else 2 if bmi < 40 else 3
    if hba1c is None and glucose is None:
        return {**base, "risk": None, "points": pts, "missing": ["HbA1c or fasting glucose"]}
    a = hba1c or 5.4
    lo, hi = (2, 5) if a < 5.5 else (9, 25) if a < 6.0 else (25, 50)
    if glucose and glucose >= 100:
        lo, hi = max(lo, 15), max(hi, 35)
    mid = (lo + hi) / 2 * (1 + 0.08 * (pts - 4))  # ADA points shift within the band
    risk = round(max(lo, min(hi, mid)), 1)
    return {**base, "risk": risk, "range": [lo, hi], "points": pts, "missing": [],
            "band": "low" if risk < 10 else "moderate" if risk < 25 else "high"}


# --------------------------------------------------------------------------- Liver fibrosis (FIB-4)
def fib4(age, ast, alt, platelets) -> dict:
    base = {"model": "FIB-4", "outcome": "Likelihood of advanced liver fibrosis",
            "citation": "Sterling RK et al. Hepatology 2006;43:1317-25."}
    if None in (age, ast, alt, platelets):
        return {**base, "risk": None, "missing": [k for k, v in {"AST": ast, "ALT": alt, "platelets": platelets}.items() if v is None]}
    v = age * ast / (platelets * math.sqrt(alt))
    band = "low (< 1.3)" if v < 1.3 else "indeterminate (1.3–2.67) — elastography advised" if v < 2.67 else "high (> 2.67)"
    return {**base, "score": round(v, 2), "band": band, "missing": [], "risk": None}


# --------------------------------------------------------------------------- Kidney failure (KFRE 4-variable)
# Tangri N et al. JAMA 2016;315:164-74 (non-North-American calibration). Applies to eGFR < 60.
def kfre(age, sex, egfr, uacr) -> dict:
    base = {"model": "Kidney Failure Risk Equation (4-variable)", "outcome": "5-year risk of kidney failure",
            "citation": "Tangri N et al. JAMA 2016;315:164-74."}
    if None in (age, egfr, uacr):
        return {**base, "risk": None, "missing": [k for k, v in {"eGFR": egfr, "UACR": uacr}.items() if v is None]}
    if egfr >= 60:
        return {**base, "risk": None, "missing": [], "band": "not applicable — kidney function is above the CKD range (eGFR ≥ 60)"}
    acr_mg_mmol = max(uacr, 0.1) * 0.113
    x = -0.2201 * (age / 10 - 7.036) + 0.2467 * ((1 if sex == "male" else 0) - 0.5642) - 0.5567 * (egfr / 5 - 7.222) \
        + 0.4510 * (math.log(acr_mg_mmol * 8.84) - 5.137)
    risk = 1 - 0.9365 ** math.exp(x)
    return {**base, "risk": round(risk * 100, 1), "missing": [], "band": "low" if risk < 0.03 else "intermediate" if risk < 0.1 else "high"}


# --------------------------------------------------------------------------- Bundle
def inputs_from_vault() -> dict:
    from . import engine
    L = engine.latest_values()
    p = engine.profile()
    n = lambda m: (L.get(m) or {}).get("value_num")
    sbp = engine.signal_baseline("sbp", days=60)
    w = (engine.series("weight") or [(None, None)])[-1][1]
    h = (p.get("height_cm") or 0) / 100
    return {"age": engine.age_on(), "sex": p.get("sex", "male"), "tc": n("chol_total"), "hdl": n("hdl"), "ldl": n("ldl"),
            "apob": n("apob"), "sbp": sbp["mean"] if sbp else None, "bp_treated": p.get("bp_treated", False),
            "smoker": p.get("smoker", False), "diabetic": False, "statin": p.get("statin", False), "hba1c": n("hba1c"), "glucose": n("glucose"),
            "bmi": round(w / (h * h), 1) if w and h else None, "family_history_dm": p.get("family_history_dm", False),
            "active": (engine.signal_baseline("exercise_min", days=30) or {"mean": 0})["mean"] >= 21,
            "ast": n("ast"), "alt": n("alt"), "platelets": n("platelets"), "egfr": n("egfr"), "uacr": n("uacr"),
            "cac": n("cac"), "lpa": n("lpa"), "hscrp": n("hscrp")}


def run(x: dict) -> dict:
    hyper = (x.get("sbp") or 0) >= 130 or x.get("bp_treated")
    cvd = ascvd_pce(x.get("age"), x.get("sex"), x.get("tc"), x.get("hdl"), x.get("sbp"), x.get("bp_treated"), x.get("smoker"), x.get("diabetic"))
    enhancers = []
    if (x.get("lpa") or 0) >= 50:
        enhancers.append("Lp(a) ≥ 50 mg/dL")
    if (x.get("hscrp") or 0) >= 2:
        enhancers.append("hs-CRP ≥ 2 mg/L")
    if (x.get("apob") or 0) >= 130:
        enhancers.append("ApoB ≥ 130 mg/dL")
    if (x.get("cac") or 0) > 0:
        enhancers.append(f"Coronary calcium {int(x['cac'])} (plaque present)")
    cvd["enhancers"] = enhancers
    cvd["caveat"] = "PCE under-estimates risk in South Asians; risk enhancers and coronary calcium refine it."
    pv = prevent(x.get("age"), x.get("sex"), x.get("tc"), x.get("hdl"), x.get("sbp"), x.get("bp_treated"), x.get("statin"),
                 x.get("diabetic"), x.get("smoker"), x.get("egfr"), x.get("bmi"))
    out = {
        "prevent": pv,
        "cvd": cvd,
        "diabetes": diabetes(x.get("age"), x.get("sex"), x.get("bmi"), x.get("hba1c"), x.get("glucose"),
                             x.get("family_history_dm"), hyper, x.get("active", True)),
        "liver": fib4(x.get("age"), x.get("ast"), x.get("alt"), x.get("platelets")),
        "kidney": kfre(x.get("age"), x.get("sex"), x.get("egfr"), x.get("uacr")),
    }
    return {"inputs": x, "models": out}


LEVERS = {  # what-if levers: (input key, label, unit, typical achievable change description)
    "tc": ("Total cholesterol", "mg/dL"), "hdl": ("HDL", "mg/dL"), "sbp": ("Systolic BP", "mmHg"),
    "hba1c": ("HbA1c", "%"), "bmi": ("BMI", "kg/m²"), "smoker": ("Smoking", ""), "active": ("150 min/week activity", ""),
    "statin": ("Statin", ""),
}


def what_if(changes: dict) -> dict:
    base = inputs_from_vault()
    scen = {**base, **{k: v for k, v in changes.items() if k in LEVERS}}
    b, s = run(base), run(scen)
    delta = {}
    for k in ("cvd", "diabetes", "kidney"):
        r0, r1 = b["models"][k].get("risk"), s["models"][k].get("risk")
        if r0 is not None and r1 is not None:
            delta[k] = {"from": r0, "to": r1, "change": round(r1 - r0, 1)}
    for h in ("ten_year", "thirty_year"):
        p0, p1 = b["models"]["prevent"].get(h), s["models"]["prevent"].get(h)
        if p0 and p1:
            delta[f"prevent_{h}"] = {o: {"from": p0[o], "to": p1[o], "change": round(p1[o] - p0[o], 1)} for o in p0}
    return {"baseline": b, "scenario": s, "delta": delta, "changes": changes}


# --------------------------------------------------------------------------- AHA PREVENT (2024), base model
# Khan SS et al. Circulation 2024;149:430-449. Coefficients from the AHA supplementary tables as packaged in
# `preventr` (Mayer MG, CRAN). Verified against the package's reference example in tests.
import json as _json
import os as _os

_PC = _json.load(open(_os.path.join(_os.path.dirname(__file__), "prevent_coef.json")))
_OUTCOMES = {"total_cvd": "Total cardiovascular disease", "ascvd": "Heart attack or stroke (ASCVD)",
             "heart_failure": "Heart failure", "chd": "Coronary heart disease", "stroke": "Stroke"}


def prevent(age, sex, tc, hdl, sbp, bp_treated=False, statin=False, diabetic=False, smoker=False, egfr=None, bmi=None) -> dict:
    base = {"model": "AHA PREVENT (2024), base model", "citation": "Khan SS et al. Circulation 2024;149:430-49."}
    need = {"age": age, "total cholesterol": tc, "HDL": hdl, "systolic BP": sbp, "eGFR": egfr, "BMI": bmi}
    missing = [k for k, v in need.items() if v is None]
    if missing:
        return {**base, "missing": missing, "ten_year": None, "thirty_year": None}
    a = (age - 55) / 10
    nh = (tc - hdl) * 0.02586 - 3.5
    h = (hdl * 0.02586 - 1.3) / 0.3
    s_lt, s_ge = (min(sbp, 110) - 110) / 20, (max(sbp, 110) - 130) / 20
    b_lt, b_ge = (min(bmi, 30) - 25) / 5, (max(bmi, 30) - 30) / 5
    e_lt, e_ge = (min(egfr, 60) - 60) / -15, (max(egfr, 60) - 90) / -15
    bp, st, dm, sm = map(lambda v: 1.0 if v else 0.0, (bp_treated, statin, diabetic, smoker))
    terms = [a, nh, h, s_lt, s_ge, dm, sm, b_lt, b_ge, e_lt, e_ge, bp, st, bp * s_ge, st * nh,
             a * nh, a * h, a * s_ge, a * dm, a * sm, a * b_ge, a * e_lt, 1.0]
    out = {**base, "missing": [], "note": "Validated for ages 30–79." if not 30 <= age <= 79 else None}
    for horizon, key in (("ten_year", "base_10yr"), ("thirty_year", "base_30yr")):
        tab = _PC[key]
        t = terms if horizon == "ten_year" else [terms[0], a * a] + terms[1:]
        res = {}
        for o in _OUTCOMES:
            col = tab.get(f"{'female' if sex == 'female' else 'male'}_{o}")
            if col is None:
                continue
            lo = sum(c * x for c, x in zip(col, t))
            res[o] = round(100 * math.exp(lo) / (1 + math.exp(lo)), 1)
        out[horizon] = res
    out["labels"] = _OUTCOMES
    return out
