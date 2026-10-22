"""Telomy-LLX clinic engine — one patient in, one grounded, doctor-gated assessment out.

Unifies every grounded engine for the doctor side:
  • DIAGNOSTICS — trained risk: blood-panel models (disease_tools) when bloods exist, else the lab-free chronic
    model (chronic_tools); plus 10-yr mortality and the wearable overlay (fusion).
  • TREATMENTS  — evidence-graded candidate interventions per flagged risk (lifestyle / referral / medication
    class to DISCUSS / monitoring). Decision-support the doctor considers — never an auto-prescription.
  • THERAPIES   — centre modalities mapped to each risk, evidence-graded, with a clinician sign-off protocol.
  • SUPPLEMENTS — biomarker-driven, safety-screened (supplements), doctor-validation payload.
  • RETEST      — which panels/markers to repeat and when.

Claims firewall (DPR §12.1): "supports / consider / discuss / tracks how your body responds" — never
"treats / cures / prescribes". Every item carries an evidence grade (A strong RCT/guideline · B moderate ·
C small/mechanistic · D insufficient) and nothing reaches the member until a clinician validates it.
"""
from __future__ import annotations

from . import disease_tools, chronic_tools
try:
    from . import supplements as _supp
except Exception:  # noqa: BLE001
    _supp = None
try:
    from . import fusion as _fusion
except Exception:  # noqa: BLE001
    _fusion = None
try:
    from . import geroprotectors as _gero   # the longevity-therapeutics corpus (drugs/peptides/sups/protocols)
except Exception:  # noqa: BLE001
    _gero = None

# condition key -> candidate interventions a doctor reviews. type: lifestyle | referral | medication_class |
# monitoring | procedure. grade: A/B/C/D. "action" is framed as a consideration, not an order.
TREATMENTS = {
    "diabetes": [
        {"type": "lifestyle", "grade": "A", "action": "Structured diet + ≥150 min/wk activity; 5–7% weight loss target", "note": "DPP-grade prevention of progression"},
        {"type": "medication_class", "grade": "A", "action": "Discuss metformin / GLP-1 class with the prescribing clinician", "note": "first-line per ADA; clinician decision"},
        {"type": "monitoring", "grade": "A", "action": "HbA1c q3 months; consider CGM for variability", "note": "integrate CGM"},
    ],
    "hypertension": [
        {"type": "lifestyle", "grade": "A", "action": "DASH-style diet, sodium <2 g/d, aerobic activity, alcohol moderation"},
        {"type": "monitoring", "grade": "A", "action": "Home/ambulatory BP logging; confirm with a validated cuff", "note": "Telomy BP trend is a screen, not a cuff"},
        {"type": "medication_class", "grade": "A", "action": "Discuss first-line antihypertensive (ACEi/ARB, CCB, thiazide) with clinician"},
    ],
    "high_cholesterol": [
        {"type": "lifestyle", "grade": "A", "action": "Mediterranean pattern, fibre, reduced saturated fat, activity"},
        {"type": "medication_class", "grade": "A", "action": "Discuss statin eligibility (ASCVD risk-based) with clinician"},
        {"type": "monitoring", "grade": "B", "action": "Lipid panel + ApoB/Lp(a) retest in 8–12 weeks"},
    ],
    "coronary_hd": [
        {"type": "referral", "grade": "A", "action": "Cardiology referral; consider coronary calcium / stress testing"},
        {"type": "lifestyle", "grade": "A", "action": "Smoking cessation, cardiac-safe exercise prescription, BP/lipid control"},
        {"type": "monitoring", "grade": "A", "action": "Continuous ECG (the patch) for ischemia/arrhythmia context"},
    ],
    "heart_failure": [
        {"type": "referral", "grade": "A", "action": "Cardiology referral; echocardiogram for EF"},
        {"type": "monitoring", "grade": "B", "action": "Daily weight, symptom + HRV trend; fluid/sodium guidance"},
    ],
    "stroke": [
        {"type": "referral", "grade": "A", "action": "Vascular/neurology review; carotid + rhythm assessment"},
        {"type": "monitoring", "grade": "A", "action": "AFib screening via the ECG patch; BP control"},
    ],
    "kidney_disease": [
        {"type": "referral", "grade": "A", "action": "Nephrology if eGFR falling; BP + glycemic control"},
        {"type": "monitoring", "grade": "A", "action": "eGFR + urine ACR retest; avoid nephrotoxins"},
    ],
    "copd": [
        {"type": "lifestyle", "grade": "A", "action": "Smoking cessation (highest-yield); pulmonary rehab"},
        {"type": "referral", "grade": "A", "action": "Spirometry to confirm; pulmonology if moderate+"},
        {"type": "monitoring", "grade": "B", "action": "Nocturnal SpO₂ (oximeter) for desaturation burden"},
    ],
    "asthma_current": [
        {"type": "referral", "grade": "A", "action": "Confirm with spirometry; inhaler technique + action plan with clinician"},
        {"type": "monitoring", "grade": "B", "action": "Trigger/symptom log; SpO₂ during exacerbation"},
    ],
    "liver_disease": [
        {"type": "lifestyle", "grade": "A", "action": "Alcohol reduction, weight loss for MASLD, metabolic control"},
        {"type": "monitoring", "grade": "B", "action": "LFTs + FIB-4; imaging/elastography if indicated"},
    ],
    "depression": [
        {"type": "referral", "grade": "A", "action": "Validated screen (PHQ-9) + clinician review; therapy referral"},
        {"type": "lifestyle", "grade": "B", "action": "Exercise prescription, sleep regularity, light exposure"},
        {"type": "monitoring", "grade": "C", "action": "HRV + sleep trend as an adjunct, not a diagnostic"},
    ],
    "arthritis": [
        {"type": "lifestyle", "grade": "A", "action": "Low-impact activity, weight management, physiotherapy"},
        {"type": "referral", "grade": "B", "action": "Rheumatology if inflammatory pattern"},
    ],
    "cancer": [
        {"type": "referral", "grade": "A", "action": "Age/risk-appropriate screening per guidelines; specialist if flagged"},
    ],
    "_mortality": [
        {"type": "lifestyle", "grade": "A", "action": "Address the top modifiable drivers (smoking, activity, BP, glycemia, sleep)"},
    ],
}

# condition key -> centre therapy modalities (evidence-graded). All require the therapy.py clinician sign-off.
THERAPIES = {
    "hypertension":   [{"modality": "exercise_rx", "grade": "A"}, {"modality": "sauna", "grade": "B", "note": "repeated sauna ↓ BP, ↓ CVD mortality (observational + small RCTs)"}, {"modality": "breathwork_hrv", "grade": "B"}],
    "coronary_hd":    [{"modality": "exercise_rx", "grade": "A"}, {"modality": "sauna", "grade": "B"}],
    "heart_failure":  [{"modality": "exercise_rx", "grade": "B", "note": "supervised only"}],
    "diabetes":       [{"modality": "exercise_rx", "grade": "A"}, {"modality": "cold_exposure", "grade": "C", "note": "glucose/insulin-sensitivity signal, small studies"}],
    "high_cholesterol": [{"modality": "exercise_rx", "grade": "A"}],
    "copd":           [{"modality": "pulmonary_rehab", "grade": "A"}, {"modality": "hbot", "grade": "D", "note": "not indicated for COPD; flag"}],
    "depression":     [{"modality": "exercise_rx", "grade": "A"}, {"modality": "red_light", "grade": "C"}, {"modality": "breathwork_hrv", "grade": "B"}],
    "arthritis":      [{"modality": "sauna", "grade": "C"}, {"modality": "cold_exposure", "grade": "B", "note": "symptomatic relief"}, {"modality": "exercise_rx", "grade": "A"}],
    "_recovery":      [{"modality": "sauna", "grade": "B"}, {"modality": "cold_exposure", "grade": "C"}, {"modality": "red_light", "grade": "C"}],
}

# normalise model condition names into the map keys
_ALIAS = {"coronary_heart_disease": "coronary_hd", "heart_attack": "coronary_hd", "angina": "coronary_hd",
          "cvd_death": "coronary_hd", "other_cancer": "cancer", "skin_cancer": "cancer"}


def _norm(c: str) -> str:
    return _ALIAS.get(c, c)


def _has_bloods(panel: dict) -> bool:
    markers = {"albumin", "creatinine", "hgb", "wbc", "alt", "chol_serum", "glucose_serum", "rdw"}
    return isinstance(panel, dict) and len(markers & set(panel)) >= 4


def assess(panel: dict | None = None, profile: dict | None = None,
           features: dict | None = None, wearable: dict | None = None,
           risk_threshold: float = 0.2) -> dict:
    """One grounded, doctor-gated assessment. Pass a blood `panel` (preferred) and/or non-invasive `features`;
    optional `profile` (meds/conditions/goals) and `wearable` (resting_hr, hrv, spo2) sharpen it."""
    panel = panel or {}
    diag: dict = {"layer": None, "ranked": [], "mortality": None, "wearable_overlay": None}

    # ---- DIAGNOSTICS ----
    if _has_bloods(panel):
        diag["layer"] = "blood_panel"
        dd = disease_tools.predict_diseases(panel, topk=8)
        diag["ranked"] = [{"condition": k, "probability": v} for k, v in dd.get("ranked", dd).items()] \
            if isinstance(dd.get("ranked", dd), dict) else dd.get("ranked", [])
        try:
            diag["mortality"] = disease_tools.mortality_risk_10y(panel)
        except Exception:  # noqa: BLE001
            pass
    elif features and chronic_tools.available():
        diag["layer"] = "chronic_lab_free"
        diag["ranked"] = chronic_tools.predict_chronic(features, topk=8).get("ranked", [])
    else:
        diag["layer"] = "insufficient"

    if wearable and _fusion is not None:
        try:
            diag["wearable_overlay"] = _fusion.risk_profile(panel or features or {}, wearable)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            diag["wearable_overlay"] = {"note": "wearable overlay unavailable"}

    # top risks above threshold
    top = []
    for r in diag["ranked"]:
        prob = r.get("probability") if isinstance(r, dict) else None
        cond = r.get("condition") if isinstance(r, dict) else None
        if cond and prob is not None and prob >= risk_threshold:
            top.append((_norm(cond), round(float(prob), 3)))

    # ---- TREATMENTS + THERAPIES per flagged risk ----
    treatments, therapies, seen = [], [], set()
    for cond, prob in top:
        if cond in seen:
            continue
        seen.add(cond)
        for t in TREATMENTS.get(cond, []):
            treatments.append({**t, "for": cond, "risk": prob})
        for th in THERAPIES.get(cond, []):
            therapies.append({**th, "for": cond, "risk": prob})
    if not therapies:
        therapies = [{**th, "for": "recovery"} for th in THERAPIES["_recovery"]]

    # ---- SUPPLEMENTS ----
    supplements = None
    if _supp is not None and _has_bloods(panel):
        try:
            supplements = _supp.recommend(panel, profile)
        except Exception:  # noqa: BLE001
            supplements = {"note": "supplement engine error"}

    # ---- LONGEVITY (geroprotector corpus) — the proactive side: right therapies/sups/drugs/protocols ----
    longevity = None
    if _gero is not None:
        try:
            bm = {**(features or {}), **(panel or {}), **(wearable or {})}
            gprofile = {"age": (profile or {}).get("age") or (panel or {}).get("age"),
                        "sex": ("M" if str((profile or {}).get("sex") or (panel or {}).get("sex") or "").upper().startswith(("M", "1")) else
                                ("F" if (profile or {}).get("sex") or (panel or {}).get("sex") else None)),
                        "goals": (profile or {}).get("goals") or ["longevity"],
                        "conditions": (profile or {}).get("conditions") or [],
                        "medications": (profile or {}).get("medications") or [],
                        "devices": (profile or {}).get("devices") or []}
            longevity = _gero.recommend(gprofile, bm)
        except Exception:  # noqa: BLE001
            longevity = {"note": "longevity corpus unavailable"}

    # ---- RETEST ----
    retest = []
    if _has_bloods(panel):
        retest.append({"what": "lipid + metabolic panel", "when": "8–12 weeks after any change", "grade": "A"})
    else:
        retest.append({"what": "baseline blood panel (CBC + CMP + lipids + HbA1c + hs-CRP)", "when": "soon", "grade": "A",
                       "why": "upgrades every risk from the lab-free screen to the trained blood models"})

    return {
        "diagnostics": diag,
        "flagged_risks": [{"condition": c, "probability": p} for c, p in top],
        "treatments": treatments,
        "therapies": therapies,
        "supplements": supplements,
        "longevity": longevity,
        "retest_plan": retest,
        "doctor_gate": {"status": "pending_validation",
                        "message": "Clinician review required before anything reaches the member.",
                        "n_items": len(treatments) + len(therapies) + (len(supplements.get("recommendations", [])) if isinstance(supplements, dict) else 0)},
        "disclaimer": "Decision-support only. Probabilities are not diagnoses; treatments and therapies are "
                      "candidates for the clinician to consider and validate.",
    }


def validate(assessment: dict, approved_items: list | None = None, doctor: str = "", note: str = "") -> dict:
    """Clinician sign-off gate: records which treatment/therapy/supplement items the doctor approved."""
    assessment = dict(assessment)
    assessment["doctor_gate"] = {"status": "validated" if approved_items else "rejected",
                                 "doctor": doctor, "note": note, "approved": approved_items or []}
    return assessment
