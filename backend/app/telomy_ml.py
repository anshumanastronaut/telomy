"""Trained-ML integration — serves the Telomy engine suite (aging/muscle clocks, disease + mortality,
fusion, supplements, modalities, food-quality, voice, check-ins) over the API, per-user.

Additive and safe: it mounts its own APIRouter (one include_router line in main.py); it never changes
the existing bioage/predict/twin routes. The /me/report endpoint reconciles the TRAINED clock with the
app's existing clinical bioage so the client shows both, clearly labelled, rather than one silently
overriding the other. All heavy imports are lazy so the app still boots if the ML extra isn't installed.
"""
from __future__ import annotations
import os
from fastapi import APIRouter, Body
from . import db

router = APIRouter(prefix="/me", tags=["telomy-ml"])

# engine panel key  <-  app catalogue marker_id aliases (first match wins). HGB handles anything missing.
_ALIAS = {
    "crp_mgL": ["hs_crp", "crp", "hscrp", "crp_hs"], "lymph_pct": ["lymph_pct", "lymphocytes_pct", "lymphocytes"],
    "neut_pct": ["neutrophil_pct", "neutrophils_pct", "neutrophils"], "mono_pct": ["monocyte_pct", "monocytes_pct"],
    "eos_pct": ["eos_pct", "eosinophils_pct"], "baso_pct": ["baso_pct", "basophils_pct"],
    "hgb": ["hemoglobin", "haemoglobin", "hgb"], "hct": ["hct", "hematocrit"],
    "total_chol": ["chol_total", "cholesterol", "total_cholesterol"], "trig": ["triglycerides", "trig"],
    "wbc": ["wbc_total", "wbc", "white_cells"], "rbc": ["rbc"], "alp": ["alp", "alkaline_phosphatase"],
    "glucose": ["glucose", "glucose_fasting", "fasting_glucose", "glucose_random"],
    "bilirubin": ["bilirubin", "bilirubin_total"], "bun": ["bun", "urea_nitrogen"],
    "vitamin_d_25oh": ["vitamin_d", "vit_d_25oh", "vitamin_d_25"], "b12": ["b12", "vitamin_b12"],
    "ferritin": ["ferritin"], "homocysteine": ["homocysteine"], "magnesium": ["magnesium"],
    # body composition -> muscular-age clock
    "almi": ["almi"], "bmi": ["bmi"], "waist": ["waist", "waist_circumference"], "weight": ["weight", "bmxwt"],
    "height": ["height", "bmxht"], "total_fat_pct": ["bca_body_fat", "body_fat_pct", "total_fat_pct"],
    "arm_circ": ["arm_circ", "arm_circumference"],
}
_IDENTITY = ["albumin", "creatinine", "hba1c", "alt", "ast", "ggt", "uric_acid",
             "calcium", "phosphorus", "sodium", "potassium", "bicarb", "total_protein",
             "globulin", "iron", "hdl", "mcv", "rdw", "platelets", "mpv"]

def _latest_results() -> dict:
    """Most-recent value per marker from the current user's Vault (bound by _bind_user)."""
    try:
        rows = db.rows("""SELECT r.marker_id AS m, r.value_num AS v
                          FROM results r LEFT JOIN reports rp ON r.report_id = rp.id
                          WHERE r.value_num IS NOT NULL
                          ORDER BY COALESCE(rp.collected_on, rp.created_at, '') ASC""")
    except Exception:
        return {}
    return {row["m"]: row["v"] for row in rows}   # later rows overwrite earlier -> most recent wins

def _panel() -> dict:
    res = _latest_results()
    panel = {k: res[k] for k in _IDENTITY if k in res}
    for key, aliases in _ALIAS.items():
        for a in aliases:
            if a in res:
                panel[key] = res[a]; break
    # age + sex from profile
    try:
        p = db.one("SELECT age, sex FROM profile WHERE id = 1")
        if p:
            if p.get("age"): panel["age"] = p["age"]
            if p.get("sex"): panel["sex"] = 1 if str(p["sex"]).lower().startswith("m") else 2
    except Exception:
        pass
    return panel

@router.get("/report")
def me_report():
    """Unified Telomy Report for the signed-in user (trained models) + the app's existing bioage, labelled."""
    from .llx import report as _report
    panel = _panel()
    if len([k for k in panel if k not in ("age", "sex")]) < 3:
        return {"status": "need_more_data", "markers_found": sorted(panel), "note": "Upload a blood report to generate your report."}
    out = {"panel_markers_used": sorted(k for k in panel if k not in ("age", "sex")), "trained": _report.analyze_report(panel)}
    try:
        from . import bioage as _bio      # the app's existing clinical bioage, for side-by-side reconciliation
        out["clinical_bioage_existing"] = _bio.summary() if hasattr(_bio, "summary") else "see /bioage"
    except Exception:
        pass
    out["note"] = "trained = NHANES-trained clocks + engines; clinical_bioage_existing = the app's guideline model. Shown side by side."
    return out

@router.post("/report/compute")
def me_report_compute(panel: dict = Body(...), wearable: dict | None = Body(None)):
    """Compute the full risk profile from a panel directly (demo/trial template + testing)."""
    from .llx import fusion as _fusion
    return _fusion.risk_profile(panel, wearable)

@router.post("/supplements")
def me_supplements(panel: dict = Body(...), profile: dict | None = Body(None)):
    from .llx import supplements as _s
    return _s.recommend(panel, profile or {})

@router.post("/foodscore")
def me_foodscore(nutrients_per_100g: dict = Body(..., embed=True)):
    from .llx import food_quality as _f
    return _f.score(nutrients_per_100g)

@router.get("/modalities")
def me_modalities(goal: str):
    from .llx import modalities as _m
    return _m.recommend_for_goal(goal)

@router.post("/checkin")
def me_checkin(now_min: int = Body(...), context: dict = Body(default={}), signals: dict = Body(default={})):
    from .llx.checkin_engine import CheckinEngine
    # stateless demo instance; production holds per-user state. Returns the decision for the app to deliver.
    return CheckinEngine().decide(now_min, context, signals) or {"prompt": None}

@router.post("/chronic")
def me_chronic(features: dict = Body(default={}), topk: int = Body(default=6)):
    """Lab-free chronic-disease screen (BRFSS 5.89M) — for members with NO recent bloods. Takes non-invasive
    features (age, sex, bmi, smoker, phys_act, sleep_hrs, hi_bp_flag, marital, state, …); missing ones default."""
    from .llx import chronic_tools as _c
    if not _c.available():
        return {"error": "chronic model not installed", "ranked": []}
    feats = dict(features)
    if "age" not in feats or "sex" not in feats:            # fall back to the profile for basics
        prof = (db.one("SELECT data FROM profile WHERE id=1") or {}).get("data")
        if prof:
            import json as _j
            p = _j.loads(prof) if isinstance(prof, str) else prof
            feats.setdefault("age", p.get("age"))
            feats.setdefault("sex", 1 if str(p.get("sex", "")).lower().startswith("m") else (2 if p.get("sex") else None))
            feats.setdefault("bmi", p.get("bmi"))
    return _c.predict_chronic({k: v for k, v in feats.items() if v is not None}, topk=topk)


@router.get("/environment")
def me_environment(name: str | None = None, lat: float | None = None, lon: float | None = None):
    """The member's exposome — air (7,482 WHO cities) + social connection + noise + UV/water + food pointer."""
    from . import exposome as _e
    if not name and lat is None:                            # default to the profile's city
        prof = (db.one("SELECT data FROM profile WHERE id=1") or {}).get("data")
        if prof:
            import json as _j
            name = (_j.loads(prof) if isinstance(prof, str) else prof).get("city")
    return _e.exposome_profile(name=name, lat=lat, lon=lon) or {"error": "could not resolve a location"}


@router.get("/organs")
def me_organs():
    """Organ-specific aging clocks — per-organ age + age-acceleration (which system is aging fastest) from the
    signed-in user's latest blood panel."""
    from .llx import organ_tools as _o
    if not _o.available():
        return {"status": "unavailable", "note": "organ clocks not installed"}
    panel = _panel()
    if len([k for k in panel if k not in ("age", "sex")]) < 4:
        return {"status": "need_more_data", "note": "Upload a blood report (CBC + metabolic panel) to see organ ages."}
    # Chronological age + sex from the profile — _panel()'s own SELECT reads columns that don't exist (profile is
    # JSON), so without this the age_acceleration the twin displays is always null. engine.age_on() computes age
    # from the stored dob, exactly as /profile does.
    from . import engine
    age = engine.age_on()
    prof = engine.profile() or {}
    if prof.get("sex"):
        panel["sex"] = 1 if str(prof["sex"]).lower().startswith("m") else 2
    return _o.organ_ages(panel, chronological_age=float(age) if age else None)


@router.post("/rhythm")
def me_rhythm(features: list = Body(..., embed=True)):
    """AFib / rhythm classifier (Normal / AF / Other / Noisy) from the 21 on-device ECG features (beat detector +
    RR stats). The phone computes the features from the last ECG window and posts them here."""
    import os as _os, joblib as _jl
    path = _os.path.join(_os.path.dirname(__file__), "assets", "afib_rhythm.joblib")
    if not _os.path.exists(path):
        return {"status": "unavailable"}
    import numpy as _np
    clf = _jl.load(path)
    p = clf.predict_proba(_np.array([features], dtype=float))[0]
    classes = ["Normal", "AF", "Other", "Noisy"]
    ranked = sorted(zip(classes, (round(float(x), 3) for x in p)), key=lambda z: -z[1])
    return {"rhythm": ranked[0][0], "probabilities": dict(ranked),
            "af_probability": round(float(p[1]), 3),
            "note": "Decision-support rhythm screen (CinC-2017-trained, AF Se 0.79/Sp 0.98) — not a diagnosis; "
                    "confirm symptomatic/high-probability results with a clinician/12-lead."}


@router.post("/longevity")
def me_longevity(goals: list = Body(default=["longevity"]), include_experimental: bool = Body(default=True)):
    """Right-therapy steering for the signed-in member: evidence-graded, safety-screened longevity interventions
    (lifestyle protocols → approved drugs → consumer supplements → experimental), tiered and ranked, built from
    the member's profile + latest biomarkers. Everything clinical/experimental is flagged doctor-gated."""
    from .llx import geroprotectors as _g
    prof = (db.one("SELECT data FROM profile WHERE id=1") or {}).get("data")
    import json as _j
    p = (_j.loads(prof) if isinstance(prof, str) else prof) or {}
    profile = {"age": p.get("age"),
               "sex": ("M" if str(p.get("sex", "")).lower().startswith("m") else ("F" if p.get("sex") else None)),
               "goals": goals or p.get("goals") or ["longevity"],
               "conditions": p.get("conditions") or [], "medications": p.get("medications") or [],
               "devices": p.get("devices") or []}
    return _g.recommend(profile, _panel(), include_experimental=include_experimental)


@router.post("/longevity/trial")
def me_longevity_trial(intervention_id: str = Body(..., embed=True)):
    """Design a proper n-of-1 self-experiment for one intervention on the signed-in member — baseline, course,
    tracked markers, washout/re-challenge, stopping rules and a response rule — so a trial is run, not a guess."""
    from .llx import geroprotectors as _g
    prof = (db.one("SELECT data FROM profile WHERE id=1") or {}).get("data")
    import json as _j
    p = (_j.loads(prof) if isinstance(prof, str) else prof) or {}
    profile = {"age": p.get("age"), "conditions": p.get("conditions") or [], "medications": p.get("medications") or [],
               "devices": p.get("devices") or []}
    return _g.design_trial(intervention_id, profile)


@router.get("/longevity/catalog")
def me_longevity_catalog(intervention_id: str | None = None):
    """Browse the evidence-graded longevity corpus — the whole catalog summary, or one intervention's full record."""
    from .llx import geroprotectors as _g
    return _g.lookup(intervention_id) if intervention_id else _g.corpus_summary()


@router.get("/longevity/safety")
def me_longevity_safety(intervention_id: str | None = None):
    """FAERS (FDA adverse-event) disproportionality signals mined from ~20.7M reports — the whole coverage
    summary, or the top signals for one drug/hormone. A monitoring/consent aid, not causation."""
    from .llx import faers_safety as _f
    if intervention_id:
        return _f.signals(intervention_id, topk=12) or {"available": False, "note": "no FAERS data for this item (e.g. a consumer supplement)"}
    return _f.summary()


@router.post("/macros")
def me_macros(intake: dict = Body(default={}), gut: dict = Body(default={}), activity: str = Body(default="moderate")):
    """Curated protein/fibre/fat fix for the signed-in member — targets + the gap + food swaps + rationale,
    tuned to their profile, routine, gut and latest biomarkers. Renal protein restriction is clinician-gated."""
    from .llx import macros as _m
    import json as _j
    prof = (db.one("SELECT data FROM profile WHERE id=1") or {}).get("data")
    p = (_j.loads(prof) if isinstance(prof, str) else prof) or {}
    profile = {"age": p.get("age"),
               "sex": ("M" if str(p.get("sex", "")).lower().startswith("m") else ("F" if p.get("sex") else None)),
               "weight_kg": p.get("weight_kg") or p.get("weight"), "height_cm": p.get("height_cm") or p.get("height"),
               "activity": activity or p.get("activity") or "moderate",
               "goals": p.get("goals") or ["longevity"], "conditions": p.get("conditions") or []}
    return _m.prescribe(profile, _panel(), intake, gut)


@router.get("/circadian")
def me_circadian(days: int = 7, target_wake_h: float = 6.5):
    """Diagnose, track and help fix the body clock from the member's continuous vitals (cosinor + nadir phase):
    circadian phase, rhythm robustness, day-to-day regularity, faults (delayed/advanced/flat/irregular) + fixes."""
    import time
    from . import circadian, vitals
    now = int(time.time()); start = now - max(1, days) * 86400
    series = {}
    for m in ("hr", "skin_temp", "hrv", "steps", "motion", "resp"):
        try:
            s = vitals.series(m, start, now, 6000)
            if s.get("n"):
                series[m] = [[p[0], p[1]] for p in s.get("points", []) if isinstance(p, (list, tuple))]
        except Exception:  # noqa: BLE001
            pass
    return circadian.assess(series, target_wake_h=target_wake_h)


@router.get("/overview")
def me_overview():
    """The signed-in member's own 360 — labs + vitals + recovery/sleep + habits + reports + a grounded AI summary,
    the same combined view the clinic sees. Read from the member's own bound Vault."""
    from . import patient_data
    return patient_data.overview_me()


@router.get("/health")
def me_ml_health():
    try:
        import sklearn, scipy, joblib  # noqa
        base = os.path.join(os.path.dirname(__file__), "assets")
        return {"ml_ready": True, "assets": sorted(os.listdir(base)) if os.path.isdir(base) else []}
    except Exception as e:
        return {"ml_ready": False, "reason": str(e)}
