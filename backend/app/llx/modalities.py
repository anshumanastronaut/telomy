"""Telomy modality engine — the hardware/biohacking side (Bonphul device suite).

Maps each wellness modality we supply to centres (cryotherapy, cold plunge, red/NIR photobiomodulation,
far-infrared sauna, HBOT, molecular hydrogen, ozone, PEMF, halotherapy, vibro-acoustic) to: its
evidence grade, what biomarkers/metrics it plausibly moves, a protocol (dose/frequency), deterministic
contraindications, and the markers to track for an n-of-1 verdict.

Honesty: there is no proprietary outcome dataset for these devices yet, so effect expectations are
LITERATURE PRIORS (graded A strong / B moderate / C preliminary / D weak-or-controversial). The engine
tracks each client's own before/after response and recalibrates the priors as centre data accrues —
the same n-of-1 loop as the supplement engine. No lifespan/cure claims; clinician-in-the-loop; the
contraindication screen is hard-coded safety, never a model output.
"""
from __future__ import annotations

# modality -> evidence + effects + protocol + safety. device = the Bonphul product line.
MODALITIES = {
    "far_infrared_sauna": {"device": "ZENITH", "grade": "B",
        "evidence": "Traditional-sauna cohorts (KIHD): 4-7x/wk assoc. up to ~60% lower CV mortality, "
                    "lower BP/stroke/dementia risk — observational, men; FIR runs cooler so this is an extrapolation.",
        "moves": ["blood_pressure↓", "resting_hr↓", "recovery↑", "sleep↑", "cardiovascular_risk↓"],
        "track": ["resting_hr", "blood_pressure", "crp_mgL", "sleep_quality"],
        "protocol": "15-30 min, 70-80°C (FIR lower), 3-7x/week; hydrate", "goals": ["cardiovascular","recovery","sleep","stress"],
        "contra": ["unstable angina","recent MI","severe aortic stenosis","uncontrolled hypotension","pregnancy","dehydration"]},
    "whole_body_cryo": {"device": "CryoGen", "grade": "B",
        "evidence": "Meta of 11 RCTs: reduces inflammatory response; hsCRP ↓ in cohort data. Mood/recovery weaker.",
        "moves": ["crp_mgL↓", "inflammation↓", "recovery↑", "soreness↓"],
        "track": ["crp_mgL", "il6", "soreness", "recovery"],
        "protocol": "2-3 min, -110 to -170°C, 2-5x/week per goal", "goals": ["inflammation","recovery"],
        "contra": ["cold urticaria","cryoglobulinemia","Raynaud's","uncontrolled hypertension","recent MI","unstable angina","peripheral neuropathy","pregnancy"]},
    "cold_plunge": {"device": "ZIMA", "grade": "B",
        "evidence": "Cold-water immersion: sleep & quality-of-life improve; mood NOT significant in meta; recovery context-dependent.",
        "moves": ["sleep↑", "quality_of_life↑", "alertness↑", "recovery↑"],
        "track": ["sleep_quality", "resting_hr", "mood", "recovery"],
        "protocol": "2-5 min, 10-15°C, 2-5x/week; avoid late-evening if it disturbs sleep", "goals": ["recovery","sleep","stress"],
        "contra": ["cold urticaria","Raynaud's","uncontrolled hypertension","recent cardiac event","pregnancy"]},
    "photobiomodulation": {"device": "AGNEE / IMMORTAL-T", "grade": "B",
        "evidence": "Red (630-670nm)/NIR (808-850nm) PBM: scars & skin-aging moderate evidence (biphasic dose - fluence matters); "
                    "pain/recovery mixed, small trials.",
        "moves": ["skin_elasticity↑", "wrinkles↓", "scar_quality↑", "local_pain↓", "recovery↑"],
        "track": ["skin_assessment", "local_pain", "recovery"],
        "protocol": "10-20 min, 630-850nm, moderate fluence, 3-5x/week; eye protection", "goals": ["skin","recovery","pain"],
        "contra": ["active cancer over the treated site","photosensitizing medication","photosensitivity disorder"]},
    "hbot": {"device": "Hyperion", "grade": "C",
        "evidence": "Small uncontrolled trial (n=35): +~20% telomere length, fewer senescent T-cells after 60 sessions; a newer "
                    "cohort +29% after 30. Longevity claims overreach the data; HBOT is APPROVED for specific clinical indications (B).",
        "moves": ["telomere_length↑(preliminary)", "senescent_cells↓(preliminary)", "tissue_oxygenation↑", "cognition↑(preliminary)"],
        "track": ["telomere_proxy", "cognitive_score", "wound_healing"],
        "protocol": "60-90 min, 2-2.5 ATA, course of 20-60 sessions; ENT clearance", "goals": ["longevity","cognitive","recovery"],
        "contra": ["untreated pneumothorax","bleomycin/doxorubicin/cisplatin chemo","recent ear/sinus surgery","uncontrolled seizures","severe COPD with bullae","claustrophobia"]},
    "molecular_hydrogen": {"device": "AERION / IMMORTAL-T", "grade": "C",
        "evidence": "81+ early clinical trials; safe; antioxidant/anti-inflammatory signals across systems but dosing unstandardized, "
                    "needs multicenter RCTs.",
        "moves": ["oxidative_stress↓", "inflammation↓", "recovery↑(preliminary)"],
        "track": ["crp_mgL", "oxidative_markers", "fatigue"],
        "protocol": "inhalation 30-60 min or H2-water; safe; handle flammability", "goals": ["inflammation","recovery","longevity"],
        "contra": ["(none established; flammability handling)"]},
    "pemf": {"device": "AERION / PEMF", "grade": "C",
        "evidence": "Established for bone healing & wound repair (B); broader wellness/recovery claims thin (C).",
        "moves": ["bone_healing↑", "wound_healing↑", "local_pain↓", "recovery↑(weak)"],
        "track": ["local_pain", "recovery", "sleep_quality"],
        "protocol": "per device program, 10-30 min, 3-5x/week", "goals": ["recovery","pain","bone"],
        "contra": ["pacemaker/ICD","pregnancy","active hemorrhage","implanted electronic device"]},
    "halotherapy": {"device": "AERION (salt)", "grade": "C",
        "evidence": "Salt therapy: preliminary respiratory benefit (FEV1, mucociliary clearance); no guidelines; more RCTs needed.",
        "moves": ["respiratory_symptoms↓(preliminary)", "mucociliary_clearance↑"],
        "track": ["respiratory_symptoms", "spo2"],
        "protocol": "30-45 min sessions, 2-3x/week", "goals": ["respiratory","relaxation"],
        "contra": ["acute respiratory infection","active tuberculosis","severe/brittle asthma"]},
    "vibroacoustic": {"device": "AERION / IMMORTAL-T", "grade": "C",
        "evidence": "Small studies: increased parasympathetic activity, reduced perceived stress; preliminary.",
        "moves": ["stress↓", "hrv↑(preliminary)", "relaxation↑"],
        "track": ["hrv", "stress", "sleep_quality"],
        "protocol": "20-40 min sessions", "goals": ["stress","sleep","relaxation"],
        "contra": ["pregnancy","acute thrombosis","pacemaker/ICD"]},
    "ozone": {"device": "AERION (O₃)", "grade": "D",
        "evidence": "Weak/controversial evidence for wellness; inhaled ozone is TOXIC; real safety concerns. Not recommended as a "
                    "general wellness offering; medical use only under qualified supervision.",
        "moves": ["(unproven for wellness)"],
        "track": [], "protocol": "medical supervision only; never inhaled", "goals": [],
        "contra": ["G6PD deficiency","hyperthyroidism","pregnancy","NEVER inhale ozone","acute MI"]},
}

def recommend_for_goal(goal: str, profile: dict | None = None) -> dict:
    """Modalities that fit a goal, evidence-graded, with a deterministic contraindication screen."""
    profile = profile or {}
    conditions = {c.lower() for c in profile.get("conditions", [])}
    meds = {m.lower() for m in profile.get("medications", [])}
    devices = {d.lower() for d in profile.get("devices", [])}        # e.g. "pacemaker"
    flags = conditions | devices
    fit, blocked = [], []
    for name, m in MODALITIES.items():
        if goal not in m["goals"]:
            continue
        hit = [c for c in m["contra"] if any(tok in flag for flag in flags for tok in [c.lower().split("/")[0].split("(")[0].strip()]) and c.lower() not in ("(none established; flammability handling)",)]
        rec = {"modality": name, "device": m["device"], "evidence_grade": m["grade"],
               "expected_effects": m["moves"], "protocol": m["protocol"],
               "track_markers": m["track"], "evidence": m["evidence"]}
        if m["grade"] == "D":
            rec["warning"] = "weak/controversial evidence — not recommended as a general wellness offering"
        if hit:
            blocked.append({"modality": name, "blocked_by": hit}); continue
        fit.append(rec)
    fit.sort(key=lambda r: {"A":0,"B":1,"C":2,"D":3}[r["evidence_grade"]])
    return {"goal": goal, "recommended": fit, "blocked_by_contraindication": blocked,
            "note": "Evidence-graded literature priors; a clinician signs off the protocol. Effects are "
                    "tracked per client (n-of-1) and the priors recalibrate as centre data accrues."}

def n_of_1(modality: str, before: dict, after: dict, weeks: float) -> dict:
    """Per-client verdict: did the tracked markers move in the expected direction over a course?"""
    m = MODALITIES.get(modality)
    if not m:
        return {"error": f"unknown modality {modality}"}
    changes, moved = [], 0
    for mk in m["track"]:
        b, a = before.get(mk), after.get(mk)
        if b in (None, "") or a in (None, ""):
            continue
        try:
            d = float(a) - float(b)
        except (TypeError, ValueError):
            continue
        changes.append({"marker": mk, "before": b, "after": a, "delta": round(d, 2)})
        # "improvement" direction is marker-specific; CRP/HR/BP/soreness/stress down = good
        good_down = any(k in mk for k in ("crp", "hr", "bp", "blood_pressure", "sore", "stress", "pain", "il6", "oxidative", "fatigue", "symptom"))
        if (good_down and d < 0) or (not good_down and d > 0):
            moved += 1
    n = len(changes)
    if weeks < 3 or n == 0:
        verdict = "too_early"
    elif moved >= max(1, (n + 1) // 2):
        verdict = "helped"
    else:
        verdict = "no_signal"
    return {"modality": modality, "device": m["device"], "verdict": verdict, "weeks": weeks,
            "markers_moved": f"{moved}/{n}", "changes": changes,
            "note": "n-of-1 signal vs this client's own baseline — not a clinical claim; feeds prior recalibration."}

if __name__ == "__main__":
    import json
    print("== cardiovascular goal ==")
    print(json.dumps(recommend_for_goal("cardiovascular"), indent=2)[:700])
    print("\n== recovery goal, client with a pacemaker ==")
    r = recommend_for_goal("recovery", {"devices": ["pacemaker"]})
    print("recommended:", [x["modality"] for x in r["recommended"]], "| blocked:", r["blocked_by_contraindication"])
    print("\n== n-of-1 sauna course (BP + RHR + CRP down) ==")
    print(json.dumps(n_of_1("far_infrared_sauna", {"resting_hr": 72, "blood_pressure": 138, "crp_mgL": 3.0},
                            {"resting_hr": 66, "blood_pressure": 128, "crp_mgL": 2.1}, weeks=8), indent=2))
