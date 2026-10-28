"""Protocols to discuss (Track B6) — a member-safe view over the evidence-graded geroprotector engine.

The hard work (matching interventions to the person's biomarkers, evidence grading, safety screening, contraindication
blocking, the prescriber gate) is already done by `llx/geroprotectors.recommend`. This wrapper just:
  · builds the member's profile + biomarkers from their labs,
  · shows FOUNDATION (lifestyle) and OPTIONAL (consumer supplements) fully — these are safe, self-directed,
  · shows CLINICAL / EXPERIMENTAL (drugs, hormones, peptides, off-label) as name + "your doctor can review this"
    ONLY — never dosing or how-to to the member, because those are clinician-gated (CDSCO/DPDP; see NEXTGEN_PLAN).
Nothing here is a prescription. Every item routes the member to discuss with their clinician.
"""
from __future__ import annotations

from . import engine
from .llx import geroprotectors

# catalog marker id → the biomarker key the geroprotector triggers use
_MAP = {
    "hba1c": "hba1c", "glucose": "glucose", "vitd": "vitamin_d_25oh", "hscrp": "crp_mgL", "tg": "trig",
    "testosterone": "total_testosterone", "ldl": "ldl", "apob": "apob", "uric_acid": "uric_acid",
    "homocysteine": "homocysteine", "ferritin": "ferritin", "b12": "vitamin_b12",
}


def _biomarkers() -> dict:
    L = engine.latest_values()
    out: dict = {}
    for mid, key in _MAP.items():
        r = L.get(mid)
        if r and r.get("value_num") is not None:
            try:
                out[key] = float(r["value_num"])
            except (TypeError, ValueError):
                pass
    # BMI from profile, if available
    p = engine.profile() or {}
    try:
        h, w = float(p.get("height_cm") or p.get("height")), float(p.get("weight_kg") or p.get("weight"))
        if h and w:
            out["bmi"] = w / (h / 100) ** 2
    except (TypeError, ValueError):
        pass
    return out


def for_member() -> dict:
    p = engine.profile() or {}
    profile = {"age": p.get("age"), "sex": p.get("sex"),
               "goals": ["longevity", "cardiovascular", "metabolic", "muscle", "cognitive"],
               "conditions": p.get("conditions", []), "medications": p.get("medications", [])}
    rec = geroprotectors.recommend(profile, _biomarkers(), include_experimental=True)
    t = rec["tiers"]

    def light(item):  # clinician-gated items: name + why only, no dosing/how-to for the member
        return {"id": item["id"], "name": item["name"], "category": item["category"], "grade": item["grade"],
                "scope": item["scope"], "why": item.get("why", []), "doctor_gate": True}

    def full(item):
        return {"id": item["id"], "name": item["name"], "category": item["category"], "status": item["status"],
                "grade": item["grade"], "scope": item["scope"], "why": item.get("why", []),
                "effect": item["effect"], "dose": item["dose"], "caution": item["caution"],
                "rationale": item.get("rationale"), "doctor_gate": item.get("doctor_gate", False)}

    foundation = [full(i) for i in t["foundation"]]
    optional = [full(i) for i in t["optional"]]
    clinician = [light(i) for i in (t["clinical"] + t["experimental"])]

    return {
        "foundation": foundation,          # lifestyle — do these first
        "supplements": optional,           # consumer supplements — biomarker-driven, discuss with clinician
        "clinician_only": clinician,       # drugs/hormones/peptides/off-label — name only, routed to the doctor
        "counts": {"foundation": len(foundation), "supplements": len(optional), "clinician_only": len(clinician)},
        "disclaimer": rec["disclaimer"],
        "note": ("Lifestyle protocols first — strongest evidence, lowest risk. Supplements are biomarker-driven; "
                 "run them past your clinician. Prescription, hormone and peptide options are shown by name only and "
                 "need a doctor on your care team to review and prescribe — we never recommend those to you directly."),
    }
