"""Telomy macronutrient-fix engine — a curated protein / fibre / fat prescription tuned to the person's needs,
routine, gut and biomarkers. Deterministic and evidence-anchored, like the supplement engine: measure → target
→ the gap ("the fix") → food swaps → safety (renal/gut) → rationale (why, from which biomarker + guideline) →
retest. Doctor-gated where it becomes clinical (renal protein restriction).

Honesty: these are nutrition targets grounded in guideline ranges (PROT-AGE/ESPEN for protein, the US DGA/IOM
for fibre, AHA/ADA for fat quality, KDIGO for renal). They "support" measured needs; benefits are on
biomarkers and function, never a disease cure. India note: adapt sources to local diet (dal/legumes, millets,
curd) — handled in the source lists.
"""
from __future__ import annotations

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "athlete": 1.9}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _kcal(profile: dict) -> tuple[float, str]:
    """Estimate maintenance kcal (Mifflin-St Jeor if height/age/sex given, else 30 kcal/kg)."""
    w = _num(profile.get("weight_kg"))
    h = _num(profile.get("height_cm"))
    age = _num(profile.get("age"))
    sex = str(profile.get("sex", "")).upper()[:1]
    act = ACTIVITY.get(str(profile.get("activity", "moderate")).lower(), 1.55)
    if w and h and age and sex in ("M", "F"):
        bmr = 10 * w + 6.25 * h - 5 * age + (5 if sex == "M" else -161)
        return round(bmr * act), "Mifflin-St Jeor × activity"
    if w:
        return round(30 * w * (act / 1.55)), "≈30 kcal/kg heuristic"
    return 2000, "default (no weight given)"


def _protein(profile, bm, renal) -> dict:
    w = _num(profile.get("weight_kg")) or 70
    age = _num(profile.get("age")) or 40
    goals = {g.lower() for g in profile.get("goals", [])}
    training = str(profile.get("activity", "")).lower() in ("active", "athlete") or "muscle" in goals
    albumin = _num(bm.get("albumin"))
    almi = _num(bm.get("almi"))

    reasons, gate = [], False
    if renal["restrict"]:
        lo, hi = 0.6, 0.8
        reasons.append(f"reduced kidney function ({renal['why']}) — protein restricted to {lo}–{hi} g/kg per KDIGO; this is a clinician-gated target, not a wellness choice")
        gate = True
    else:
        lo, hi = 1.2, 1.6                                   # healthy-adult longevity floor (PROT-AGE/ESPEN)
        reasons.append("1.2–1.6 g/kg is the healthy-adult range for preserving lean mass (PROT-AGE/ESPEN)")
        if training or "muscle" in goals:
            hi = 2.0
            reasons.append("training / muscle goal → up to ~2.0 g/kg supports muscle protein synthesis")
        if age >= 65:
            lo = max(lo, 1.2)
            reasons.append("age ≥65 → hold the higher end; older muscle has anabolic resistance")
        if albumin is not None and albumin < 4.0:
            reasons.append(f"albumin {albumin} g/dL (low-normal) — bias to the higher end and check intake is actually reaching the target")
        if almi is not None and almi < 7.0:
            reasons.append(f"ALMI {almi} (low lean mass / sarcopenia signal) — pair the higher protein target with resistance training")
    g_lo, g_hi = round(w * lo), round(w * hi)
    return {
        "nutrient": "protein", "target_g_per_kg": [lo, hi], "target_g_per_day": [g_lo, g_hi],
        "per_meal_g": round(w * 0.4), "meals": "spread across 3–4 meals, ~0.4 g/kg each, leucine-rich",
        "sources": ["eggs", "fish", "chicken", "curd/yogurt & paneer", "dal/legumes", "soy/tofu", "whey or plant protein if short"],
        "supplement_if_short": "20–30 g whey or plant protein to close a daily gap",
        "doctor_gate": gate, "rationale": reasons,
    }


def _fibre(profile, bm, intake, gut) -> dict:
    kcal, _ = _kcal(profile)
    target = max(25, round(14 * kcal / 1000))               # 14 g / 1000 kcal (US DGA)
    sex = str(profile.get("sex", "")).upper()[:1]
    if sex == "M":
        target = max(target, 30)
    current = _num(intake.get("fibre_g_per_day"))
    ldl = _num(bm.get("ldl")) or _num(bm.get("ldl_c"))
    apob = _num(bm.get("apob"))
    hba1c = _num(bm.get("hba1c"))
    bristol = _num(gut.get("bristol"))
    ibs = any(k in {c.lower() for c in gut.get("conditions", [])} for k in ("ibs", "sibo"))
    bloating = bool(gut.get("bloating"))

    reasons, emphasis = [], []
    reasons.append(f"target {target} g/day (14 g per 1000 kcal, US Dietary Guidelines); most adults get ~15 g")
    if (ldl and ldl > 100) or (apob and apob > 90):
        emphasis.append("soluble/viscous (oats β-glucan, psyllium, barley, legumes)")
        reasons.append(f"{'ApoB '+str(apob) if apob else 'LDL '+str(ldl)} elevated → viscous soluble fibre lowers LDL/ApoB (bile-acid binding)")
    if hba1c and hba1c >= 5.7:
        emphasis.append("viscous fibre with carb-containing meals")
        reasons.append(f"HbA1c {hba1c}% → viscous fibre blunts the post-prandial glucose rise")
    if bristol is not None and bristol <= 2:
        emphasis.append("insoluble (whole grains, vegetable skins, nuts/seeds) + more water")
        reasons.append("hard/infrequent stool (Bristol ≤2) → add insoluble fibre and fluid")
    if ibs or bloating:
        emphasis.append("gentle, lower-FODMAP soluble (oats, psyllium, kiwi) — not a fermentable bolus")
        reasons.append("IBS/bloating → favour soluble over highly fermentable fibre and titrate very slowly (consider dietitian/low-FODMAP)")
    else:
        emphasis.append("plant diversity (aim ~30 different plants/week) + a fermented food daily")
        reasons.append("diverse plants + fermented foods feed a broader microbiome (short-chain-fatty-acid producers)")

    titration = None
    if current is not None and target - current > 8:
        titration = f"you're at ~{round(current)} g — increase by ~5 g/week toward {target} g to avoid gas/bloating, with extra water"
        reasons.append(titration)
    return {
        "nutrient": "fibre", "target_g_per_day": target, "current_g_per_day": (round(current) if current is not None else None),
        "emphasis": emphasis, "titration": titration,
        "sources": ["legumes/dal", "oats & barley", "whole fruit (incl. kiwi, berries)", "vegetables with skin",
                    "nuts & seeds (chia, flax)", "psyllium husk if short"],
        "doctor_gate": False, "rationale": reasons,
    }


def _fat(profile, bm) -> dict:
    kcal, _ = _kcal(profile)
    ldl = _num(bm.get("ldl")) or _num(bm.get("ldl_c"))
    apob = _num(bm.get("apob"))
    trig = _num(bm.get("trig")) or _num(bm.get("triglycerides"))
    o3 = _num(bm.get("omega3_index"))

    reasons, fix = [], []
    pct = [25, 35]
    reasons.append("total fat ~25–35% of calories; the quality matters more than the amount")
    if (ldl and ldl > 100) or (apob and apob > 90):
        fix.append("cut saturated fat to <7% of calories (less butter/ghee, fatty red & processed meat, coconut/palm)")
        fix.append("replace it with mono-unsaturated fat (olive oil, nuts, avocado) + soluble fibre")
        reasons.append(f"{'ApoB '+str(apob) if apob else 'LDL '+str(ldl)} elevated → saturated-fat→MUFA swap lowers ApoB, the causal lipid (AHA)")
    if trig and trig > 150:
        fix.append("reduce refined carbs, sugar and alcohol (the biggest triglyceride drivers)")
        fix.append("add omega-3 (oily fish 2–3×/wk, or EPA/DHA 2–4 g/day for high triglycerides, clinician-guided)")
        reasons.append(f"triglycerides {trig} mg/dL → carbohydrate/alcohol restriction + omega-3 is the lever (AHA)")
    if o3 is not None and o3 < 8:
        fix.append("raise omega-3 intake (oily fish or EPA/DHA) toward an omega-3 index ≥8%")
        reasons.append(f"omega-3 index {o3}% (<8% target) → more EPA/DHA")
    if not fix:
        fix.append("keep fats mostly unsaturated (olive oil, nuts, seeds, oily fish); minimise trans & ultra-processed")
        reasons.append("lipids in range → maintain an unsaturated-fat pattern")
    return {
        "nutrient": "fat", "target_pct_kcal": pct, "fix": fix,
        "sources": ["olive oil", "nuts & seeds", "avocado", "oily fish (salmon, sardine, mackerel)"],
        "avoid": ["trans fat / partially hydrogenated oils", "excess saturated fat if ApoB/LDL high", "deep-fried & ultra-processed"],
        "doctor_gate": False, "rationale": reasons,
    }


def prescribe(profile: dict | None = None, biomarkers: dict | None = None,
              intake: dict | None = None, gut: dict | None = None) -> dict:
    """Curated protein/fibre/fat targets + the fix, tuned to needs, routine, gut and biomarkers.

    profile:    {age, sex, weight_kg, height_cm, activity[sedentary..athlete], goals[], conditions[]}
    biomarkers: {albumin, almi, ldl/apob, trig, hba1c, omega3_index, egfr, creatinine, crp_mgL, ...}
    intake:     {fibre_g_per_day, protein_g_per_day, ...}  (optional current intake, to compute the gap)
    gut:        {bristol(1-7), bloating(bool), conditions[](ibs/sibo), diversity}  (optional)
    """
    profile = profile or {}
    bm = biomarkers or {}
    intake = intake or {}
    gut = gut or {}
    conditions = {c.lower() for c in profile.get("conditions", [])}
    egfr = _num(bm.get("egfr"))
    creat = _num(bm.get("creatinine"))
    renal = {"restrict": bool(any(k in conditions for k in ("ckd", "kidney disease", "renal"))
                               or (egfr is not None and egfr < 60)
                               or (creat is not None and creat > 1.5)),
             "why": (f"eGFR {egfr}" if egfr is not None and egfr < 60 else
                     (f"creatinine {creat}" if creat is not None and creat > 1.5 else "known CKD"))}

    kcal, kcal_note = _kcal(profile)
    protein = _protein(profile, bm, renal)
    fibre = _fibre(profile, bm, intake, gut)
    fat = _fat(profile, bm)

    retest = [{"marker": "lipid panel + ApoB", "weeks": 12, "why": "see the fat/fibre fix land"},
              {"marker": "HbA1c", "weeks": 12, "why": "fibre + carb-quality effect"}]
    if protein["doctor_gate"]:
        retest.append({"marker": "eGFR + urine ACR", "weeks": 12, "why": "renal protein target is clinician-monitored"})

    return {
        "energy": {"maintenance_kcal": kcal, "basis": kcal_note},
        "protein": protein, "fibre": fibre, "fat": fat,
        "routine_fit": {
            "training_days": "put ~0.4 g/kg protein within a few hours of resistance training; carbs around the session",
            "fasting_window": "hit the daily protein target inside your eating window — don't let TRE cost you protein",
        },
        "retest_plan": retest,
        "doctor_gate": {"status": "pending_validation" if protein["doctor_gate"] else "informational",
                        "message": ("Renal protein restriction must be set and monitored by a clinician."
                                    if protein["doctor_gate"] else
                                    "Dietary guidance; a clinician/dietitian reviews before it ships to the member.")},
        "disclaimer": "Nutrition targets grounded in guideline ranges (PROT-AGE/ESPEN, US DGA, AHA/ADA, KDIGO). "
                      "They support measured needs and move biomarkers — not a treatment of disease. Sources are "
                      "adaptable to the member's diet (veg/non-veg, Indian staples).",
    }


if __name__ == "__main__":
    import json
    print("== 46M, muscle+metabolic, high ApoB + prediabetic + low fibre + constipation ==")
    out = prescribe(
        {"age": 46, "sex": "M", "weight_kg": 82, "height_cm": 178, "activity": "active", "goals": ["muscle", "metabolic"]},
        {"apob": 110, "hba1c": 5.9, "trig": 180, "albumin": 4.1, "almi": 6.9, "omega3_index": 4.5},
        {"fibre_g_per_day": 15}, {"bristol": 2})
    print(json.dumps(out, indent=2))
    print("\n== 70F with CKD (eGFR 48) — protein must be clinician-gated ==")
    out2 = prescribe({"age": 70, "sex": "F", "weight_kg": 62, "activity": "light", "goals": ["longevity"], "conditions": ["CKD"]},
                     {"egfr": 48, "ldl": 95})
    print("protein target:", out2["protein"]["target_g_per_kg"], "| gate:", out2["protein"]["doctor_gate"])
    print("protein rationale:", out2["protein"]["rationale"][0])
