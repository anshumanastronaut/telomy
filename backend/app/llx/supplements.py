"""Telomy curated-supplement engine — biomarker-driven, safety-gated, clinician-validated.

Flow: blood/biomarker panel (+ optional profile: meds, conditions, goals) -> evidence-graded
recommendations -> deterministic safety screen (interactions, contraindications, confounders) ->
a DOCTOR-VALIDATION payload (nothing ships without a clinician's sign-off, like an Rx) -> a
recalibration plan (which markers to retest and when). Adherence + feedback close the monthly/
quarterly loop.

Honesty (grounded in the evidence): recommendations correct measured deficiencies / elevated markers;
benefits are shown mostly on biomarker *levels*, not hard clinical outcomes, so claims stay at
"supports / helps restore", never "treats/cures". India = FSSAI nutraceutical (wellness claims only;
drug-interaction warnings mandatory). This engine proposes; a doctor validates; then we ship + track.
"""
from __future__ import annotations

# evidence grade: A strong · B moderate · C limited. Each rule is deterministic and auditable.
# condition(panel) -> fires; supplement/dose/why/grade + retest marker & weeks + safety hooks.
RULES = [
    {"id": "vit_d", "marker": "vitamin_d_25oh", "fires": lambda v: v is not None and v < 30,
     "severe": lambda v: v < 20, "supp": "Vitamin D3", "dose": "2000 IU/day (<20: 4000 IU/day, recheck 8–12 wk)",
     "why": "25-OH vitamin D below sufficiency (30 ng/mL)", "grade": "A",
     "retest": ("vitamin_d_25oh", 12), "contra": ["hypercalcemia", "sarcoidosis"], "interactions": []},
    {"id": "b12", "marker": "b12", "fires": lambda v: v is not None and v < 250,
     "severe": lambda v: v < 150, "supp": "Vitamin B12 (methylcobalamin)", "dose": "1000 µg/day",
     "why": "serum B12 below 250 pg/mL", "grade": "A", "retest": ("b12", 12),
     "contra": [], "interactions": [], "flag_if_severe": "very low B12 — rule out pernicious anaemia / malabsorption with your doctor"},
    {"id": "iron", "marker": "ferritin", "fires": lambda v: v is not None and v < 30,
     "severe": lambda v: v < 15, "supp": "Iron (ferrous bisglycinate)", "dose": "25–50 mg elemental/day with vitamin C",
     "why": "ferritin below 30 ng/mL (iron deficiency)", "grade": "A", "retest": ("ferritin", 10),
     "contra": ["hemochromatosis"], "interactions": ["levothyroxine", "tetracycline", "quinolone"],
     "confounder": ("crp_mgL", 5.0, "ferritin rises with inflammation — with CRP elevated this low value may be unreliable; confirm iron studies with your doctor before starting iron")},
    {"id": "folate_b", "marker": "homocysteine", "fires": lambda v: v is not None and v > 12,
     "severe": lambda v: v > 20, "supp": "B-complex (folate + B12 + B6)", "dose": "folate 400 µg + B12 500 µg + B6 2 mg/day",
     "why": "homocysteine above 12 µmol/L (B-vitamin status)", "grade": "B", "retest": ("homocysteine", 12),
     "contra": [], "interactions": []},
    {"id": "omega3", "marker": "trig", "fires": lambda v: v is not None and v > 150,
     "severe": lambda v: v > 200, "supp": "Omega-3 (EPA/DHA)", "dose": "1–2 g/day",
     "why": "triglycerides above 150 mg/dL", "grade": "B", "retest": ("trig", 12),
     "contra": [], "interactions": ["warfarin", "apixaban", "clopidogrel"]},
    {"id": "magnesium", "marker": "magnesium", "fires": lambda v: v is not None and v < 1.8,
     "severe": lambda v: v < 1.5, "supp": "Magnesium glycinate", "dose": "200–400 mg/day",
     "why": "serum magnesium below 1.8 mg/dL", "grade": "B", "retest": ("magnesium", 8),
     "contra": [], "interactions": [], "renal_caution": True},
    {"id": "protein", "marker": "albumin", "fires": lambda v: v is not None and v < 4.0,
     "severe": lambda v: v < 3.5, "supp": "Protein (whey or plant) + adequate dietary protein",
     "dose": "aim 1.2–1.6 g/kg/day; 20–30 g supplemental if intake is short",
     "why": "albumin below 4.0 g/dL and/or low lean mass (sarcopenia signal)", "grade": "B",
     "retest": ("albumin", 12), "contra": [], "interactions": [], "renal_caution": True},
    {"id": "glycemic", "marker": "hba1c", "fires": lambda v: v is not None and 5.7 <= v < 6.5,
     "severe": lambda v: v >= 6.5, "supp": "Berberine or myo-inositol + lifestyle", "dose": "per clinician",
     "why": "HbA1c in the prediabetes range (5.7–6.4%)", "grade": "B", "retest": ("hba1c", 12),
     "contra": [], "interactions": ["metformin"], "flag_if_severe": "HbA1c in the diabetes range — this is a clinical matter, not a supplement; see your doctor"},
]

def recommend(panel: dict, profile: dict | None = None) -> dict:
    """Return a doctor-validation payload: evidence-graded supplement recommendations + safety flags."""
    profile = profile or {}
    meds = {m.lower() for m in profile.get("medications", [])}
    conditions = {c.lower() for c in profile.get("conditions", [])}
    renal = any(k in conditions for k in ("ckd", "kidney disease", "renal")) or \
        (panel.get("creatinine") is not None and float(panel["creatinine"]) > 1.5)
    recs, blocked = [], []
    for r in RULES:
        v = panel.get(r["marker"])
        try:
            v = float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            v = None
        if v is None or not r["fires"](v):
            continue
        rec = {"supplement": r["supp"], "dose": r["dose"], "reason": f"{r['why']} ({r['marker']}={v})",
               "evidence_grade": r["grade"], "severe": bool(r["severe"](v)), "safety": []}
        # confounder (e.g. ferritin masked by inflammation)
        if r.get("confounder"):
            cm, thr, msg = r["confounder"]
            cv = panel.get(cm)
            if cv is not None and float(cv) > thr:
                rec["safety"].append("confounded: " + msg)
        # contraindications from the user's conditions
        contra_hit = [c for c in r.get("contra", []) if c in conditions]
        if contra_hit:
            blocked.append({"supplement": r["supp"], "blocked_by": contra_hit}); continue
        # drug interactions from the user's meds
        inter = [m for m in r.get("interactions", []) if any(m in med for med in meds)]
        if inter:
            rec["safety"].append(f"interaction with {', '.join(inter)} — separate timing / clinician review")
        if r.get("renal_caution") and renal:
            rec["safety"].append("reduced kidney function — dose with caution under clinician supervision")
        if r.get("flag_if_severe") and r["severe"](v):
            rec["safety"].append(r["flag_if_severe"])
        rec["retest"] = {"marker": r["retest"][0], "weeks": r["retest"][1]}
        # ground the dose against what the market actually sells (NIH DSLD), when available
        try:
            from . import dsld
            key = dsld.RULE_TO_DSLD.get(r["id"])
            chk = dsld.dose_check(key, r["dose"]) if key else None
            if chk:
                rec["market_dose_norm"] = chk
                if "above the typical" in chk.get("note", ""):
                    rec["safety"].append("dose above the typical market range — confirm with clinician")
        except Exception:
            pass
        recs.append(rec)
    return {"recommendations": recs, "blocked_by_contraindication": blocked,
            "status": "AWAITING_DOCTOR_VALIDATION",
            "note": "Supplements support measured deficiencies; benefits are on biomarker levels, not a "
                    "treatment of disease. Nothing ships until a clinician validates this pack (FSSAI "
                    "nutraceutical; drug-interaction warnings apply).",
            "recalibration": recalibration_plan(recs)}

def recalibration_plan(recs: list) -> dict:
    """When to retest which markers, and the review cadence for the whole pack."""
    retests = sorted({(r["retest"]["marker"], r["retest"]["weeks"]) for r in recs if "retest" in r},
                     key=lambda x: x[1])
    cadence = "monthly adherence check-in; biomarker retest at the earliest due marker, then a full " \
              "pack review quarterly (or half-yearly once stable)"
    return {"retests": [{"marker": m, "due_weeks": w} for m, w in retests], "review_cadence": cadence}

def apply_doctor_decision(payload: dict, approved: bool, note: str = "") -> dict:
    """Clinician gate — only an approved pack is cleared to ship + track."""
    if not note.strip():
        return {"error": "a clinician note is required to validate or reject"}
    payload = dict(payload)
    payload["status"] = "CLEARED_TO_SHIP" if approved else "REJECTED"
    payload["doctor_note"] = note
    return payload

if __name__ == "__main__":
    import json
    panel = {"vitamin_d_25oh": 17, "b12": 210, "ferritin": 22, "crp_mgL": 7.0, "homocysteine": 16,
             "trig": 190, "magnesium": 1.9, "albumin": 3.8, "hba1c": 6.0, "creatinine": 1.1}
    profile = {"medications": ["Levothyroxine 50mcg", "Warfarin"], "conditions": [], "goals": ["energy", "metabolic"]}
    out = recommend(panel, profile)
    print(json.dumps(out, indent=2))
