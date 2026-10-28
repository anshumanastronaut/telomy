"""Point-of-care clinical calculators — deterministic, cited, no LLM. Each score is reimplemented from the primary
literature (formulas aren't copyrightable; we never copy MDCalc's text/UI). Pure functions keep them testable.

A calculator = {name, about, ref, inputs[], fn}. fn(values) -> {result, unit?, interpretation, risk?, detail?}.
`risk` is one of low/moderate/high/critical for colour coding. Nothing here is a directive — it reports the score and
its usual interpretation; clinical correlation is the clinician's call.
"""
from __future__ import annotations

import math
from typing import Any, Callable


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _b(v: Any) -> bool:
    return v is True or v == 1 or str(v).lower() in ("1", "true", "yes", "y")


# ---------------------------------------------------------------- cardiology / stroke / bleeding

def chadsvasc(v: dict) -> dict:
    age = _num(v.get("age"))
    s = 0
    s += 2 if age >= 75 else 1 if age >= 65 else 0
    s += 1 if str(v.get("sex", "")).lower().startswith("f") else 0
    for k, pts in (("chf", 1), ("htn", 1), ("stroke", 2), ("vascular", 1), ("diabetes", 1)):
        if _b(v.get(k)):
            s += pts
    risk = "low" if s == 0 else "moderate" if s == 1 else "high"
    note = {0: "Low risk.", 1: "Consider anticoagulation (shared decision)."}.get(s, "Oral anticoagulation generally recommended.")
    return {"result": s, "unit": "points", "interpretation": f"CHA₂DS₂-VASc {s}. {note}", "risk": risk}


def hasbled(v: dict) -> dict:
    s = sum(1 for k in ("htn", "renal", "liver", "stroke", "bleeding", "labile_inr", "elderly", "drugs", "alcohol") if _b(v.get(k)))
    risk = "low" if s <= 2 else "high"
    return {"result": s, "unit": "points", "risk": risk,
            "interpretation": f"HAS-BLED {s}. {'High bleeding risk — caution and address modifiable factors.' if s >= 3 else 'Lower bleeding risk.'}"}


def wells_pe(v: dict) -> dict:
    s = 0.0
    s += 3 if _b(v.get("dvt_signs")) else 0
    s += 3 if _b(v.get("pe_most_likely")) else 0
    s += 1.5 if _b(v.get("hr_over_100")) else 0
    s += 1.5 if _b(v.get("immobilization")) else 0
    s += 1.5 if _b(v.get("prior_vte")) else 0
    s += 1 if _b(v.get("hemoptysis")) else 0
    s += 1 if _b(v.get("malignancy")) else 0
    tier = "PE unlikely" if s <= 4 else "PE likely"
    return {"result": s, "unit": "points", "risk": "low" if s <= 4 else "high",
            "interpretation": f"Wells PE {s:g} — {tier}. (≤4 unlikely → consider D-dimer; >4 likely → imaging.)"}


def curb65(v: dict) -> dict:
    s = sum(1 for k in ("confusion", "urea_high", "rr_30", "low_bp") if _b(v.get(k)))
    s += 1 if _num(v.get("age")) >= 65 else 0
    risk = "low" if s <= 1 else "moderate" if s == 2 else "high"
    disp = {0: "outpatient", 1: "outpatient", 2: "consider admission", 3: "admit", 4: "admit / consider ICU", 5: "admit / consider ICU"}[s]
    return {"result": s, "unit": "points", "risk": risk, "interpretation": f"CURB-65 {s} — {disp}."}


def news2(v: dict) -> dict:
    rr, spo2, sbp, hr, temp = (_num(v.get(k)) for k in ("rr", "spo2", "sbp", "hr", "temp"))
    s = 0
    s += 3 if rr <= 8 else 1 if rr <= 11 else 0 if rr <= 20 else 2 if rr <= 24 else 3
    s += 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0
    s += 3 if sbp <= 90 else 2 if sbp <= 100 else 1 if sbp <= 110 else 0 if sbp <= 219 else 3
    s += 3 if hr <= 40 else 1 if hr <= 50 else 0 if hr <= 90 else 1 if hr <= 110 else 2 if hr <= 130 else 3
    s += 3 if temp <= 35 else 1 if temp <= 36 else 0 if temp <= 38 else 1 if temp <= 39 else 2
    if _b(v.get("altered_consciousness")):
        s += 3
    if _b(v.get("on_oxygen")):
        s += 2
    risk = "low" if s <= 4 else "moderate" if s <= 6 else "high"
    return {"result": s, "unit": "points", "risk": risk,
            "interpretation": f"NEWS2 {s} — {'low' if s<=4 else 'medium' if s<=6 else 'high'} clinical risk."}


def centor(v: dict) -> dict:
    s = sum(1 for k in ("tonsillar_exudate", "tender_nodes", "fever", "no_cough") if _b(v.get(k)))
    age = _num(v.get("age"))
    s += 1 if age < 15 else 0 if age < 45 else -1
    risk = "low" if s <= 1 else "moderate" if s <= 3 else "high"
    return {"result": s, "unit": "points", "risk": risk,
            "interpretation": f"McIsaac/Centor {s} — {'strep unlikely; no testing' if s<=1 else 'consider rapid strep test' if s<=3 else 'high likelihood; test/treat'}."}


# ---------------------------------------------------------------- renal / hepatic / metabolic

def ckd_epi(v: dict) -> dict:
    scr = _num(v.get("creatinine"))
    age = _num(v.get("age"))
    female = str(v.get("sex", "")).lower().startswith("f")
    if scr <= 0 or age <= 0:
        return {"result": None, "interpretation": "Enter creatinine (mg/dL), age and sex."}
    k = 0.7 if female else 0.9
    a = -0.241 if female else -0.302
    egfr = 142 * (min(scr / k, 1) ** a) * (max(scr / k, 1) ** -1.200) * (0.9938 ** age) * (1.012 if female else 1)
    g = egfr
    stage = ("G1 ≥90" if g >= 90 else "G2 60–89" if g >= 60 else "G3a 45–59" if g >= 45 else
             "G3b 30–44" if g >= 30 else "G4 15–29" if g >= 15 else "G5 <15")
    risk = "low" if g >= 60 else "moderate" if g >= 30 else "high"
    return {"result": round(egfr, 1), "unit": "mL/min/1.73m²", "risk": risk,
            "interpretation": f"eGFR {egfr:.0f} (CKD-EPI 2021, race-free) — {stage}."}


def fib4(v: dict) -> dict:
    age, ast, alt, plt = (_num(v.get(k)) for k in ("age", "ast", "alt", "plt"))
    if min(age, ast, alt, plt) <= 0:
        return {"result": None, "interpretation": "Enter age, AST, ALT (U/L) and platelets (10⁹/L)."}
    val = (age * ast) / (plt * math.sqrt(alt))
    risk = "low" if val < 1.3 else "moderate" if val <= 2.67 else "high"
    interp = ("advanced fibrosis unlikely" if val < 1.3 else "indeterminate — consider elastography" if val <= 2.67 else "advanced fibrosis likely")
    return {"result": round(val, 2), "unit": "", "risk": risk, "interpretation": f"FIB-4 {val:.2f} — {interp}."}


def meld_na(v: dict) -> dict:
    bili = max(1.0, _num(v.get("bilirubin")))
    inr = max(1.0, _num(v.get("inr")))
    scr = min(4.0, max(1.0, _num(v.get("creatinine"))))
    na = min(137, max(125, _num(v.get("sodium"), 137)))
    if _b(v.get("dialysis")):
        scr = 4.0
    meld = 10 * (0.957 * math.log(scr) + 0.378 * math.log(bili) + 1.120 * math.log(inr)) + 6.43
    meld = round(meld)
    meld_na_val = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    val = max(6, min(40, round(meld_na_val)))
    risk = "low" if val < 15 else "moderate" if val < 25 else "high"
    return {"result": val, "unit": "points", "risk": risk,
            "interpretation": f"MELD-Na {val} — higher = greater 90-day mortality; used for transplant prioritisation."}


def anion_gap(v: dict) -> dict:
    na, cl, hco3 = (_num(v.get(k)) for k in ("sodium", "chloride", "bicarbonate"))
    alb = _num(v.get("albumin"), 4.0)
    ag = na - (cl + hco3)
    corr = ag + 2.5 * (4.0 - alb)
    risk = "low" if corr <= 12 else "moderate"
    return {"result": round(ag, 1), "unit": "mmol/L", "risk": risk,
            "interpretation": f"Anion gap {ag:.0f} (albumin-corrected {corr:.0f}). {'Normal' if corr<=12 else 'High anion gap — workup for metabolic acidosis'}."}


def corrected_calcium(v: dict) -> dict:
    ca = _num(v.get("calcium"))
    alb = _num(v.get("albumin"), 4.0)
    corr = ca + 0.8 * (4.0 - alb)
    return {"result": round(corr, 2), "unit": "mg/dL",
            "interpretation": f"Corrected calcium {corr:.2f} mg/dL (measured {ca:.2f}, albumin {alb:.1f})."}


def qtc(v: dict) -> dict:
    qt = _num(v.get("qt"))     # ms
    hr = _num(v.get("hr"))
    if qt <= 0 or hr <= 0:
        return {"result": None, "interpretation": "Enter QT (ms) and heart rate (bpm)."}
    rr = 60.0 / hr
    bazett = qt / math.sqrt(rr)
    fridericia = qt / (rr ** (1 / 3))
    female = str(v.get("sex", "")).lower().startswith("f")
    hi = 470 if female else 450
    risk = "low" if bazett < hi else "moderate" if bazett < 500 else "high"
    return {"result": round(bazett), "unit": "ms (Bazett)", "risk": risk,
            "detail": f"Fridericia {fridericia:.0f} ms",
            "interpretation": f"QTc {bazett:.0f} ms (Bazett). {'Prolonged — review QT-prolonging drugs/electrolytes' if bazett>=hi else 'Within normal limits'}."}


def bmi(v: dict) -> dict:
    kg = _num(v.get("weight"))
    cm = _num(v.get("height"))
    if kg <= 0 or cm <= 0:
        return {"result": None, "interpretation": "Enter weight (kg) and height (cm)."}
    b = kg / (cm / 100) ** 2
    # WHO + Asian/India cut-offs noted (India: overweight ≥23, obese ≥25 per ICMR)
    cat = ("underweight" if b < 18.5 else "normal" if b < 23 else "overweight (Asian ≥23)" if b < 25 else "obese (Asian ≥25)")
    risk = "low" if b < 23 else "moderate" if b < 27.5 else "high"
    return {"result": round(b, 1), "unit": "kg/m²", "risk": risk,
            "interpretation": f"BMI {b:.1f} — {cat}. (WHO Asian/ICMR India cut-offs.)"}


# ---------------------------------------------------------------- mental health screens

def _sum_items(v: dict, n: int) -> int:
    return int(sum(_num(v.get(f"q{i}")) for i in range(1, n + 1)))


def phq9(v: dict) -> dict:
    s = _sum_items(v, 9)
    sev = ("none–minimal" if s < 5 else "mild" if s < 10 else "moderate" if s < 15 else "moderately severe" if s < 20 else "severe")
    risk = "low" if s < 10 else "moderate" if s < 20 else "high"
    flag = " ⚠ item 9 (self-harm) positive — assess safety." if _num(v.get("q9")) >= 1 else ""
    return {"result": s, "unit": "/27", "risk": risk, "interpretation": f"PHQ-9 {s}/27 — {sev} depression.{flag}"}


def gad7(v: dict) -> dict:
    s = _sum_items(v, 7)
    sev = ("minimal" if s < 5 else "mild" if s < 10 else "moderate" if s < 15 else "severe")
    risk = "low" if s < 10 else "moderate" if s < 15 else "high"
    return {"result": s, "unit": "/21", "risk": risk, "interpretation": f"GAD-7 {s}/21 — {sev} anxiety."}


# ---------------------------------------------------------------- registry

def _I(key, label, typ="number", unit="", options=None):
    d = {"key": key, "label": label, "type": typ}
    if unit:
        d["unit"] = unit
    if options:
        d["options"] = options
    return d


_YN = "bool"
CALC: dict[str, dict] = {
    "chadsvasc": {"name": "CHA₂DS₂-VASc", "cat": "Cardiology", "about": "Stroke risk in non-valvular atrial fibrillation.",
        "ref": "Lip 2010", "fn": chadsvasc, "inputs": [
            _I("age", "Age", unit="years"), _I("sex", "Sex", "enum", options=["male", "female"]),
            _I("chf", "Congestive heart failure", _YN), _I("htn", "Hypertension", _YN), _I("stroke", "Prior stroke/TIA/thromboembolism", _YN),
            _I("vascular", "Vascular disease", _YN), _I("diabetes", "Diabetes", _YN)]},
    "hasbled": {"name": "HAS-BLED", "cat": "Cardiology", "about": "Major bleeding risk on anticoagulation.", "ref": "Pisters 2010",
        "fn": hasbled, "inputs": [_I(k, lbl, _YN) for k, lbl in [
            ("htn", "Uncontrolled hypertension"), ("renal", "Abnormal renal function"), ("liver", "Abnormal liver function"),
            ("stroke", "Prior stroke"), ("bleeding", "Bleeding history/predisposition"), ("labile_inr", "Labile INR"),
            ("elderly", "Age > 65"), ("drugs", "Antiplatelet/NSAID use"), ("alcohol", "Alcohol ≥8 drinks/wk")]]},
    "wells_pe": {"name": "Wells score (PE)", "cat": "Pulmonary", "about": "Pre-test probability of pulmonary embolism.", "ref": "Wells 2000",
        "fn": wells_pe, "inputs": [_I(k, lbl, _YN) for k, lbl in [
            ("dvt_signs", "Clinical signs of DVT"), ("pe_most_likely", "PE is the most likely diagnosis"), ("hr_over_100", "Heart rate > 100"),
            ("immobilization", "Immobilisation/surgery in past 4 wks"), ("prior_vte", "Previous DVT/PE"), ("hemoptysis", "Haemoptysis"),
            ("malignancy", "Active malignancy")]]},
    "curb65": {"name": "CURB-65", "cat": "Pulmonary", "about": "Community-acquired pneumonia severity & disposition.", "ref": "Lim 2003",
        "fn": curb65, "inputs": [_I("age", "Age", unit="years"), _I("confusion", "Confusion", _YN), _I("urea_high", "Urea > 7 mmol/L (BUN >19)", _YN),
            _I("rr_30", "Respiratory rate ≥ 30", _YN), _I("low_bp", "SBP < 90 or DBP ≤ 60", _YN)]},
    "news2": {"name": "NEWS2", "cat": "Acute care", "about": "Early warning score for clinical deterioration.", "ref": "RCP 2017",
        "fn": news2, "inputs": [_I("rr", "Respiratory rate", unit="/min"), _I("spo2", "SpO₂", unit="%"), _I("sbp", "Systolic BP", unit="mmHg"),
            _I("hr", "Heart rate", unit="bpm"), _I("temp", "Temperature", unit="°C"), _I("on_oxygen", "On supplemental O₂", _YN),
            _I("altered_consciousness", "New confusion/altered consciousness", _YN)]},
    "centor": {"name": "Centor (McIsaac)", "cat": "Infectious", "about": "Likelihood of group-A strep pharyngitis.", "ref": "McIsaac 1998",
        "fn": centor, "inputs": [_I("age", "Age", unit="years"), _I("tonsillar_exudate", "Tonsillar exudate", _YN),
            _I("tender_nodes", "Tender anterior cervical nodes", _YN), _I("fever", "Fever > 38°C", _YN), _I("no_cough", "Absence of cough", _YN)]},
    "ckd_epi": {"name": "eGFR (CKD-EPI 2021)", "cat": "Renal", "about": "Race-free estimated GFR from creatinine.", "ref": "Inker 2021",
        "fn": ckd_epi, "inputs": [_I("creatinine", "Serum creatinine", unit="mg/dL"), _I("age", "Age", unit="years"),
            _I("sex", "Sex", "enum", options=["male", "female"])]},
    "fib4": {"name": "FIB-4", "cat": "Hepatology", "about": "Non-invasive estimate of hepatic fibrosis.", "ref": "Sterling 2006",
        "fn": fib4, "inputs": [_I("age", "Age", unit="years"), _I("ast", "AST", unit="U/L"), _I("alt", "ALT", unit="U/L"),
            _I("plt", "Platelets", unit="10⁹/L")]},
    "meld_na": {"name": "MELD-Na", "cat": "Hepatology", "about": "End-stage liver disease severity / transplant priority.", "ref": "Kim 2008",
        "fn": meld_na, "inputs": [_I("bilirubin", "Bilirubin", unit="mg/dL"), _I("inr", "INR"), _I("creatinine", "Creatinine", unit="mg/dL"),
            _I("sodium", "Sodium", unit="mmol/L"), _I("dialysis", "Dialysis ≥2× in past week", _YN)]},
    "anion_gap": {"name": "Anion gap", "cat": "Metabolic", "about": "Albumin-corrected serum anion gap.", "ref": "Figge 1998",
        "fn": anion_gap, "inputs": [_I("sodium", "Sodium", unit="mmol/L"), _I("chloride", "Chloride", unit="mmol/L"),
            _I("bicarbonate", "Bicarbonate", unit="mmol/L"), _I("albumin", "Albumin", unit="g/dL")]},
    "corrected_calcium": {"name": "Corrected calcium", "cat": "Metabolic", "about": "Calcium corrected for albumin.", "ref": "Payne 1973",
        "fn": corrected_calcium, "inputs": [_I("calcium", "Total calcium", unit="mg/dL"), _I("albumin", "Albumin", unit="g/dL")]},
    "qtc": {"name": "QTc", "cat": "Cardiology", "about": "Rate-corrected QT interval (Bazett & Fridericia).", "ref": "Bazett 1920",
        "fn": qtc, "inputs": [_I("qt", "QT interval", unit="ms"), _I("hr", "Heart rate", unit="bpm"),
            _I("sex", "Sex", "enum", options=["male", "female"])]},
    "bmi": {"name": "BMI", "cat": "General", "about": "Body mass index with WHO Asian/ICMR cut-offs.", "ref": "WHO; ICMR",
        "fn": bmi, "inputs": [_I("weight", "Weight", unit="kg"), _I("height", "Height", unit="cm")]},
    "phq9": {"name": "PHQ-9", "cat": "Mental health", "about": "Depression severity screen (0–3 per item).", "ref": "Kroenke 2001",
        "fn": phq9, "inputs": [_I(f"q{i}", f"Item {i} (0–3)") for i in range(1, 10)]},
    "gad7": {"name": "GAD-7", "cat": "Mental health", "about": "Anxiety severity screen (0–3 per item).", "ref": "Spitzer 2006",
        "fn": gad7, "inputs": [_I(f"q{i}", f"Item {i} (0–3)") for i in range(1, 8)]},
}

DISCLAIMER = "Calculator output supports, and does not replace, clinical judgement. Verify inputs and interpret in context."


def list_all() -> list[dict]:
    return [{"id": cid, "name": c["name"], "cat": c["cat"], "about": c["about"], "ref": c["ref"],
             "inputs": c["inputs"]} for cid, c in CALC.items()]


def compute(cid: str, values: dict) -> dict:
    c = CALC.get(cid)
    if not c:
        return {"error": "Unknown calculator."}
    out = c["fn"](values or {})
    return {"id": cid, "name": c["name"], "ref": c["ref"], **out, "disclaimer": DISCLAIMER}
