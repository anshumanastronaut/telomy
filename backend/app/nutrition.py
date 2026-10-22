"""Personal nutrition targets — computed from the person's real body, labs and measured activity, then closed-loop.

Energy: Mifflin–St Jeor (1990) resting energy × physical-activity level (PAL) from REAL movement — mean daily steps
(Apple Health) and WHOOP all-day strain when present: PAL 1.4 (<5k steps) … 1.9 (≥15k or strain ≥ 14). Goal: maintain,
or lose ~0.5 kg/week (−500 kcal/day, never below resting energy × 1.2).
Protein: 1.6 g/kg (ISSN 2017; Morton 2018 meta-analysis — no added gain above ~1.6 with resistance training); when
BMI > 27 the reference weight is the weight at BMI 25, so a high body weight doesn't inflate the target.
Fibre: 14 g per 1 000 kcal (IOM 2005), at least 30 g. Fat 25–30 % of energy, saturated fat < 10 % (WHO 2023),
added sugar < 5 % ideal / < 10 % limit (WHO 2015), sodium < 2 000 mg (WHO 2023). Carbohydrate = the remainder,
kept within 45–55 % (ICMR-NIN 2020 dietary guidelines for Indians).
Lab-aware: findings change WHAT TO TEST or which foods to emphasise; supplements are only proposed by the Rx engine
(evidence-gated, doctor-signed). Nothing here is a prescription.
"""
from datetime import date, timedelta

from . import db, engine


def _mean(metric: str, days: int):
    b = engine.signal_baseline(metric, days=days)
    return b["mean"] if b else None


def _lab(marker: str):
    return db.one("""SELECT r.value_num AS v, r.ref_low AS lo, r.ref_high AS hi, r.status AS s, rp.collected_on AS d
                     FROM results r JOIN reports rp ON rp.id = r.report_id WHERE r.marker_id = ? AND r.value_num IS NOT NULL
                     ORDER BY rp.is_test_data ASC, rp.collected_on DESC LIMIT 1""", (marker,))


def targets(goal: str = "maintain") -> dict:
    p = engine.profile()
    age = engine.age_on()
    sex = p.get("sex")
    h = p.get("height_cm")
    w = (engine.series("weight") or [(None, p.get("weight_kg"))])[-1][1] or p.get("weight_kg")
    missing = [k for k, v in {"date of birth": age, "sex": sex, "height": h, "weight": w}.items() if not v]
    if missing:
        return {"ok": False, "missing": missing, "reason": "Add " + ", ".join(missing) + " in About you to compute your targets."}
    bmr = 10 * w + 6.25 * h - 5 * age + (5 if sex == "male" else -161)
    steps = _mean("steps", 14)
    strain = None
    try:
        from . import whoop_day
        wd = whoop_day.day()
        strain = wd.get("strain") if wd.get("ok") else None
    except Exception:  # noqa: BLE001 — no WHOOP data
        pass
    if strain is not None and strain >= 14 or (steps or 0) >= 15000:
        pal, why = 1.9, "very active (≥ 15 000 steps or high daily strain)"
    elif (steps or 0) >= 10000 or (strain or 0) >= 10:
        pal, why = 1.7, "active (≥ 10 000 steps or moderate daily strain)"
    elif (steps or 0) >= 5000 or (strain or 0) >= 6:
        pal, why = 1.55, "moderately active"
    elif steps is None and strain is None:
        pal, why = 1.5, "no activity data yet — light-activity assumption until steps or WHOOP strain arrive"
    else:
        pal, why = 1.4, "mostly sedentary (< 5 000 steps)"
    tdee = bmr * pal
    kcal = tdee if goal == "maintain" else max(bmr * 1.2, tdee - 500)
    bmi = w / (h / 100) ** 2
    ref_w = 25 * (h / 100) ** 2 if bmi > 27 else w
    protein = round(1.6 * ref_w)
    fibre = max(30, round(14 * kcal / 1000))
    fat = round(0.28 * kcal / 9)
    sat_fat = round(0.10 * kcal / 9)
    carbs = round((kcal - protein * 4 - fat * 9) / 4)
    carb_pct = carbs * 4 / kcal
    notes = []
    if carb_pct > 0.55:
        carbs = round(0.55 * kcal / 4); notes.append("Carbohydrate capped at 55 % of energy (ICMR-NIN 2020).")
    lab_notes = _lab_notes(sex)
    return {"ok": True, "goal": goal, "kcal": round(kcal), "bmr": round(bmr), "pal": pal, "pal_why": why, "tdee": round(tdee),
            "bmi": round(bmi, 1), "reference_weight": round(ref_w, 1),
            "protein_g": protein, "protein_per_meal_g": round(protein / 3), "fibre_g": fibre, "carbs_g": carbs, "fat_g": fat,
            "sat_fat_max_g": sat_fat, "added_sugar_max_g": round(0.05 * kcal / 4), "sodium_max_mg": 2000, "water_l": round(0.033 * w, 1),
            "notes": notes, "labs": lab_notes,
            "sources": ["Mifflin MD et al. 1990, Am J Clin Nutr", "Morton RW et al. 2018, Br J Sports Med (protein)", "IOM 2005 (fibre)",
                        "ICMR-NIN 2020 Dietary Guidelines for Indians", "WHO 2015/2023 (sugar, saturated fat, sodium)"]}


def _lab_notes(sex: str | None) -> list[dict]:
    """What the person's own labs mean for food and for further tests. Never prescribes; points to the doctor where needed."""
    out = []
    def add(marker, text, kind="food"):
        out.append({"marker": marker, "kind": kind, "text": text})
    mcv, rdw, hb, ferr = _lab("mcv"), _lab("rdw"), _lab("hemoglobin"), _lab("ferritin")
    if mcv and mcv["lo"] and mcv["v"] < mcv["lo"] and not ferr:
        add("mcv", "Red cells are slightly small (MCV below range). Iron is the usual first suspect: ask for ferritin and an iron panel "
                   "before taking iron. Meanwhile pair iron-rich foods (dal, rajma, greens, eggs, meat) with vitamin C and keep tea/coffee "
                   "away from meals.", "test")
    plt = _lab("platelets")
    if plt and plt["lo"] and plt["v"] < plt["lo"]:
        add("platelets", "Platelets are below range — see a doctor for a repeat count and peripheral smear before starting any supplement "
                         "(fish oil, high-dose vitamin E, ginkgo and curcumin can thin the blood).", "doctor")
    anc = _lab("anc")
    if anc and anc["lo"] and anc["v"] < anc["lo"]:
        add("anc", "Neutrophils are low: B12, folate and copper deficiencies can contribute — ask your doctor whether to test them.", "test")
    alp = _lab("alp")
    if alp and alp["lo"] and alp["v"] < alp["lo"]:
        add("alp", "ALP slightly low: zinc and magnesium status can lower it; nuts, seeds, legumes and whole grains cover both.", "food")
    tsh = _lab("tsh")
    if tsh and tsh["hi"] and tsh["v"] > 0.9 * tsh["hi"]:
        add("tsh", "TSH is at the top of normal: use iodised salt (not extra iodine supplements) and recheck in 6–12 months.", "test")
    k = _lab("potassium")
    if k and k["hi"] and k["v"] > 0.93 * k["hi"]:
        add("potassium", "Potassium is high-normal: no potassium supplements or salt substitutes (they are potassium chloride).", "food")
    vd = _lab("vitd")
    if not vd:
        add("vitd", "Vitamin D was not measured — common deficiency in India; worth adding to the next test.", "test")
    return out


def today_vs_targets(goal: str = "maintain") -> dict:
    """Logged meals today (meals table, analysed by food.analyze) against the targets."""
    t = targets(goal)
    if not t.get("ok"):
        return t
    d0 = date.today().isoformat()
    tot = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fibre_g": 0.0}
    import json
    for m in db.rows("SELECT analysis FROM meals WHERE substr(ts,1,10) = ?", (d0,)):
        a = json.loads(m["analysis"] or "{}")          # food.analyze puts kcal, protein… at the top level
        for k, src in (("kcal", "kcal"), ("protein_g", "protein"), ("carbs_g", "carbs"), ("fat_g", "fat"), ("fibre_g", "fibre")):
            tot[k] += float(a.get(src) or 0)
    return {"targets": t, "eaten": {k: round(v) for k, v in tot.items()},
            "left": {k: round(t[k] - tot[k]) for k in ("kcal", "protein_g", "fibre_g", "carbs_g", "fat_g")}}
