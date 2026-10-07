"""Telomy Twin — a personal digital twin that lives what you live.

Design (Björnsson 2020 Genome Med; Corral-Acero 2020 Eur Heart J): a hybrid twin = mechanistic physiology + the person's
own data, continuously recalibrated. Validated building blocks we reuse rather than invent:
  • first-order kinetics toward a lifestyle/drug-dependent steady state, with literature time constants (τ);
  • NIH body-weight dynamics (Hall 2011, Lancet): ~22 kcal/day per kg at steady state, ~1-year time constant;
  • statin/ezetimibe LDL lowering (CTT 2010; STELLAR 2003; IMPROVE-IT 2015); psyllium (Jovanovski 2018);
  • HbA1c ↔ mean glucose (ADAG, Nathan 2008); weight-loss → HbA1c (Look AHEAD); DPP metformin;
  • vitamin D dose-response ~1 ng/mL per 100 IU at steady state (Heaney 2003), half-life ~3 weeks;
  • omega-3 index +~2 points per g/day EPA+DHA (Harris & von Schacky 2004; Flock 2013), RBC turnover ~4 months;
  • BP: −1 mmHg/kg (Neter 2003), alcohol reduction (Roerecke 2017), aerobic training (Cornelissen 2013), ARB;
  • liver fat: −~6 % relative per 1 % weight lost (Patel 2016), exercise without weight loss (Keating 2012);
  • lean mass with resistance training + protein (Morton 2018), ageing sarcopenia; BMD loss with age, smoking, alcohol;
  • VO₂max training response (~+10–15 % in 12 weeks), ageing ~1 %/year; smoking cessation weight gain (Aubin 2012, BMJ);
  • caffeine t½ ~5 h, nicotine t½ ~2 h, Widmark alcohol model with ~0.015 %/h elimination;
  • PhenoAge (Levine 2018) and AHA PREVENT / PCE recomputed from the twin's projected values.
Personalisation: the twin replays the person's own history and learns gains (e.g. how much *their* vitamin D rose per
1,000 IU; *their* HRV cost of an alcohol night, from the engine's adjusted effects). Every projection carries an
uncertainty band and the evidence behind each lever. It is a decision aid, not a diagnosis.
"""
import math
from datetime import date, timedelta

from . import db, engine, predict

# state: label, unit, τ days, lower-is-better?
STATE = {
    "weight": ("Weight", "kg", 365, True), "fat_kg": ("Fat mass", "kg", 365, True), "lean_kg": ("Lean mass", "kg", 120, False),
    "vat": ("Visceral fat", "cm²", 300, True), "almi": ("Appendicular lean mass index", "kg/m²", 120, False),
    "ldl": ("LDL cholesterol", "mg/dL", 14, True), "apob": ("ApoB", "mg/dL", 14, True), "hdl": ("HDL cholesterol", "mg/dL", 60, False),
    "tg": ("Triglycerides", "mg/dL", 21, True), "hba1c": ("HbA1c", "%", 35, True), "glucose": ("Fasting glucose", "mg/dL", 35, True),
    "vitd": ("Vitamin D", "ng/mL", 25, False), "omega3": ("Omega-3 index", "%", 40, False), "hscrp": ("hs-CRP", "mg/L", 30, True),
    "sbp": ("Systolic BP", "mmHg", 21, True), "pdff": ("Liver fat (MRI-PDFF)", "%", 60, True), "vo2": ("VO₂ max", "mL/kg/min", 42, False),
    "hrv": ("Night HRV", "ms", 14, False), "rhr": ("Resting heart rate", "bpm", 21, True), "sleep": ("Sleep", "h", 7, False),
    "bmd_t": ("Bone density (spine T-score)", "SD", None, False),
}
LEVERS = {  # id: label, kind, options
    "cig_per_day": ("Cigarettes per day", "number", [0, 2, 5, 10, 20]), "alcohol_g_week": ("Alcohol (g/week)", "number", [0, 40, 80, 114, 200]),
    "zone2_min_week": ("Zone 2 cardio (min/week)", "number", [0, 90, 150, 240]), "intervals_per_week": ("Interval sessions/week", "number", [0, 1, 2]),
    "strength_per_week": ("Strength sessions/week", "number", [0, 2, 3]), "protein_g_kg": ("Protein (g/kg/day)", "number", [0.8, 1.2, 1.6]),
    "kcal_change": ("Calories vs now (kcal/day)", "number", [-500, -300, 0, 300]), "sleep_h": ("Sleep (h)", "number", [6, 7, 7.5, 8]),
    "psyllium_g": ("Psyllium (g/day)", "number", [0, 5, 10]), "vitd_iu": ("Vitamin D3 (IU/day)", "number", [0, 2000, 4000]),
    "omega3_g": ("Omega-3 EPA+DHA (g/day)", "number", [0, 1, 2, 3]), "statin": ("Statin", "choice", ["none", "rosuva5", "rosuva10", "rosuva20"]),
    "ezetimibe": ("Ezetimibe", "bool", None), "telmisartan": ("Telmisartan 40 mg", "bool", None), "metformin": ("Metformin", "bool", None),
    "glp1": ("Semaglutide (GLP-1)", "bool", None), "sauna_per_week": ("Sauna sessions/week", "number", [0, 2, 4]),
    "late_caffeine": ("Coffee after 2 pm", "bool", None), "city": ("Home city", "choice", ["Bengaluru", "Delhi", "Mumbai", "Chennai"]),
}
PRESETS = {
    "quit_smoking": ("Quit smoking", {"cig_per_day": 0}),
    "alcohol_once": ("Alcohol once a week", {"alcohol_g_week": 38}),
    "statin": ("Start rosuvastatin 10 mg", {"statin": "rosuva10"}),
    "strength": ("Strength 3×/week + protein 1.6 g/kg", {"strength_per_week": 3, "protein_g_kg": 1.6}),
    "cardio": ("Zone 2 150 min + 1 interval session", {"zone2_min_week": 150, "intervals_per_week": 1}),
    "telomy_plan": ("Telomy plan (all of the above + psyllium, D3 4,000 IU, 7.5 h sleep, no late coffee)",
                    {"cig_per_day": 0, "alcohol_g_week": 38, "statin": "rosuva10", "strength_per_week": 3, "protein_g_kg": 1.6, "zone2_min_week": 150,
                     "intervals_per_week": 1, "psyllium_g": 10, "vitd_iu": 4000, "sleep_h": 7.5, "late_caffeine": False}),
    "move_delhi": ("Move to Delhi", {"city": "Delhi"}),
}
STATIN = {"none": 0, "rosuva5": 0.38, "rosuva10": 0.46, "rosuva20": 0.52}


# ----------------------------------------------------------------------------- the person, as the twin sees them

def inputs_now() -> dict:
    """Current lifestyle & drug inputs from the Vault: routine, events, signals, medications, profile."""
    from . import routine
    p = engine.profile()
    r = routine.active()
    m = (r or {}).get("metrics", {})
    day = date.fromisoformat(engine.last_signal_day())
    since = (day - timedelta(days=30)).isoformat()
    ev = lambda k: len(db.rows("SELECT DISTINCT substr(ts,1,10) AS d FROM events WHERE kind = ? AND ts >= ?", (k, since)))  # noqa: E731
    meds = " ".join(x["name"].lower() + " " + (x["dose"] or "").lower() for x in db.rows("SELECT name, dose FROM medications WHERE active = 1"))
    ex = engine.signal_baseline("exercise_min", days=30)
    sl = engine.signal_baseline("sleep_hours", days=30)
    alcohol_g = m.get("alcohol_g_week")
    if alcohol_g is None:
        alcohol_g = round(ev("alcohol") / 30 * 7 * 30, 1)  # ~30 g per logged drinking night
    return {
        "cig_per_day": m.get("cigarettes_per_day") if m.get("cigarettes_per_day") is not None else (p.get("cigarettes_per_day") or (10 if p.get("smoker") else 0)),
        "alcohol_g_week": alcohol_g, "zone2_min_week": round((ex["mean"] if ex else 25) * 7 * 0.6),
        "intervals_per_week": round(ev("workout_hard") / 30 * 7 / 2, 1), "strength_per_week": round(ev("workout_hard") / 30 * 7 / 2, 1),
        "protein_g_kg": 1.0, "kcal_change": 0, "sleep_h": round(sl["mean"], 2) if sl else 7.0,
        "psyllium_g": 5 if "psyllium" in meds else 0, "vitd_iu": 2000 if "vitamin d" in meds else 0,
        "omega3_g": 2 if "omega" in meds else 0, "statin": "rosuva10" if "rosuva" in meds else "none", "ezetimibe": "ezetimibe" in meds,
        "telmisartan": "telmisartan" in meds, "metformin": "metformin" in meds, "glp1": "semaglutide" in meds,
        "sauna_per_week": round(ev("sauna") / 30 * 7, 1), "late_caffeine": ev("caffeine_late") >= 4, "city": p.get("city", "Bengaluru"),
    }


def state_now() -> dict:
    L = engine.latest_values()
    v = lambda k: (L.get(k) or {}).get("value_num")  # noqa: E731
    sig = lambda k, d=30: (engine.signal_baseline(k, days=d) or {}).get("mean")  # noqa: E731
    w = (engine.series("weight") or [(None, 80.0)])[-1][1]
    bf = v("body_fat_pct") or v("bca_body_fat") or 22
    fat = w * bf / 100
    return {"weight": w, "fat_kg": round(fat, 1), "lean_kg": round(w - fat, 1), "vat": v("vat_area") or 100, "almi": v("almi") or 8,
            "ldl": v("ldl") or 120, "apob": v("apob") or 100, "hdl": v("hdl") or 45, "tg": v("tg") or 150, "hba1c": v("hba1c") or 5.5,
            "glucose": v("glucose") or 95, "vitd": v("vitd") or 25, "omega3": v("omega3_index") or 5, "hscrp": v("hscrp") or 1.5,
            "sbp": sig("sbp", 60) or 125, "pdff": v("liver_pdff") or 5, "vo2": v("vo2max_lab") or sig("vo2max", 60) or 40, "hrv": sig("hrv") or 50,
            "rhr": sig("rhr") or 60, "sleep": sig("sleep_hours") or 7, "bmd_t": v("bmd_spine_t") if v("bmd_spine_t") is not None else 0.0,
            # held constant unless a lever moves them (for PhenoAge / PREVENT)
            "_albumin": v("albumin") or 4.5, "_creatinine": v("creatinine") or 1.0, "_lymph_pct": v("lymph_pct") or 30, "_mcv": v("mcv") or 90,
            "_rdw": v("rdw") or 13, "_alp": v("alp") or 70, "_wbc": v("wbc") or 6.5, "_tc": v("chol_total") or 200, "_egfr": v("egfr") or 95}


def calibration() -> dict:
    """Personal gains learned from the person's own history (population prior = 1.0)."""
    cal = {"vitd_response": 1.0, "vitd_note": "population prior", "hrv_per_alcohol_night": -6.0, "hrv_alcohol_note": "population prior",
           "hrv_per_sauna": 2.0, "sleep_per_late_caffeine": -0.3, "hrv_per_sleep_hour": 4.0}
    hist = [(h["collected_on"], h["value_num"]) for h in engine.marker_history("vitd") if h["value_num"] is not None]
    start = db.one("SELECT ts, data FROM events WHERE kind = 'supplement' AND label LIKE '%Vitamin D%' ORDER BY ts")
    if len(hist) >= 2 and start:
        d0, v0 = hist[0]
        d1, v1 = hist[-1]
        days = (date.fromisoformat(d1) - date.fromisoformat(start["ts"][:10])).days
        dose = 2000
        expected = dose / 100 * 1.0 * (1 - math.exp(-max(days, 1) / 25))
        if expected > 0 and days > 30:
            cal["vitd_response"] = round(max(0.1, min(2.0, (v1 - v0) / expected)), 2)
            cal["vitd_note"] = (f"Your vitamin D rose {v1 - v0:+.0f} ng/mL on {dose:,} IU over {days} days; the population expects ≈ +{expected:.0f}. "
                                f"Your response is {cal['vitd_response']:.0%} of average (absorption, BMI, VDR genotype and dose timing all matter).")
    for r in engine.effect_table():
        if r["event"] == "alcohol" and r["metric"] == "hrv":
            cal["hrv_per_alcohol_night"], cal["hrv_alcohol_note"] = r["effect"], f"from your data: {r['effect']:+} ms per drinking night ({r['p_text']})"
        if r["event"] == "sauna" and r["metric"] == "hrv":
            cal["hrv_per_sauna"] = r["effect"]
        if r["event"] == "caffeine_late" and r["metric"] == "sleep_hours":
            cal["sleep_per_late_caffeine"] = r["effect"]
    return cal


# ----------------------------------------------------------------------------- physiology: steady-state targets

def targets(x0: dict, L0: dict, L: dict, cal: dict, years: float) -> tuple[dict, dict]:
    """Where each variable heads under lifestyle L (relative to the current lifestyle L0 that produced x0), plus ageing."""
    d = lambda k: (L.get(k) or 0) - (L0.get(k) or 0)  # noqa: E731
    age = (engine.age_on() or 40) + years
    sex = engine.profile().get("sex", "male")
    t, why = dict(x0), {}
    # --- energy balance → weight (Hall 2011): alcohol 7 kcal/g; activity with ~50 % compensation; quitting smoking +4.5 kg
    kcal = d("kcal_change") + d("alcohol_g_week") * 7 / 7 - 0.5 * (d("zone2_min_week") * 7 + d("intervals_per_week") * 120 + d("strength_per_week") * 150) / 7
    quit = (L0.get("cig_per_day") or 0) > 0 and (L.get("cig_per_day") or 0) == 0
    glp = (1 if L.get("glp1") else 0) - (1 if L0.get("glp1") else 0)
    dw = kcal / 22 + (4.5 if quit else 0) - 0.15 * x0["weight"] * glp
    t["weight"] = x0["weight"] + dw
    lean_gain = (min(L.get("strength_per_week") or 0, 3) - min(L0.get("strength_per_week") or 0, 3)) / 3 * (1.6 + 0.6 * (d("protein_g_kg") > 0))
    lean_age = -0.004 * x0["lean_kg"] * max(0, age - 40) / 1 * min(years, 10) / max(years, 1e-6) if age > 40 else 0
    t["lean_kg"] = x0["lean_kg"] + lean_gain + 0.25 * min(dw, 0) + lean_age
    t["fat_kg"] = t["weight"] - t["lean_kg"]
    rel_fat = t["fat_kg"] / x0["fat_kg"]
    # visceral fat tracks fat change (exponent 1.3 for energy-balance change; post-cessation gain is mostly subcutaneous → 0.6)
    rel_q = (x0["fat_kg"] + 0.75 * (4.5 if quit else 0)) / x0["fat_kg"]
    t["vat"] = x0["vat"] * (rel_fat / rel_q) ** 1.3 * rel_q ** 0.6 * (1 - 0.06 * min(1, max(0, d("zone2_min_week")) / 150))
    t["almi"] = x0["almi"] * t["lean_kg"] / x0["lean_kg"]
    if dw:
        why["weight"] = f"{dw:+.1f} kg at steady state (energy balance{' + smoking-cessation gain' if quit else ''})"
    # --- lipids
    st0, st1 = STATIN[L0.get("statin", "none")], STATIN[L.get("statin", "none")]
    ldl_mult = (1 - st1) / (1 - st0)
    ldl_mult *= (0.8 if L.get("ezetimibe") and not L0.get("ezetimibe") else 1) * (1 - 0.007 * d("psyllium_g"))
    t["ldl"] = x0["ldl"] * ldl_mult - 1.5 * max(0, -dw)
    t["apob"] = x0["apob"] * (0.85 * ldl_mult + 0.15) - 1.0 * max(0, -dw)
    t["hdl"] = x0["hdl"] + (4 if quit else 0) + 0.025 * d("zone2_min_week") / 6 + 0.04 * d("alcohol_g_week") / 7
    t["tg"] = x0["tg"] * (1 + 0.005 * d("alcohol_g_week") / 7 * 10 / 10) * (1 - 0.075 * d("omega3_g")) * (1 - 0.1 * min(1, max(0, d("zone2_min_week")) / 150)) - 2 * max(0, -dw)
    if ldl_mult != 1:
        why["ldl"] = f"LDL ×{ldl_mult:.2f} (statin/ezetimibe/fibre, CTT 2010; IMPROVE-IT; Jovanovski 2018)"
    # --- glycaemia (ADAG: eAG = 28.7·A1c − 46.7)
    da1c = 0.1 * min(dw, 0) / 1 * 1 + (-0.15 * min(1, max(0, d("zone2_min_week") + 60 * d("strength_per_week")) / 150)) + (-0.15 if L.get("metformin") and not L0.get("metformin") else 0) \
        + (-0.35 * glp) + (0.1 * max(0, 7 - L.get("sleep_h", 7)) - 0.1 * max(0, 7 - L0.get("sleep_h", 7))) + (-0.08 if quit else 0) + 0.008 * years
    t["hba1c"] = x0["hba1c"] + da1c
    t["glucose"] = x0["glucose"] + 0.6 * 28.7 * da1c
    # --- vitamin D, omega-3 (personal vitamin D gain)
    t["vitd"] = x0["vitd"] + cal["vitd_response"] * d("vitd_iu") / 100 * (0.7 if x0["weight"] / ((engine.profile().get("height_cm") or 175) / 100) ** 2 >= 25 else 1)
    t["omega3"] = x0["omega3"] + 2.0 * d("omega3_g")
    # --- inflammation
    crp = x0["hscrp"] * (0.75 if quit else 1) * (1 - 0.15 * min(1, max(0, d("zone2_min_week")) / 150)) * (1 - (0.3 if st1 > st0 else 0)) * (1 + 0.004 * d("alcohol_g_week") / 7 * 10 / 10)
    t["hscrp"] = max(0.2, crp - 0.13 * max(0, -dw))
    # --- blood pressure (Neter 2003; Roerecke 2017; Cornelissen 2013; ARB)
    from . import exposome
    pm0 = exposome.CITIES.get(L0.get("city"), exposome.CITIES["Bengaluru"])[3]
    pm1 = exposome.CITIES.get(L.get("city"), exposome.CITIES["Bengaluru"])[3]
    t["sbp"] = x0["sbp"] + 1.0 * dw + (0.02 * d("alcohol_g_week") / 7 * 7 if d("alcohol_g_week") < 0 else 0.03 * d("alcohol_g_week") / 7 * 7) / 7 * 7 \
        - 5 * min(1, max(0, d("zone2_min_week")) / 150) - (10 if L.get("telmisartan") and not L0.get("telmisartan") else 0) \
        - 1.5 * max(0, d("sauna_per_week")) / 2 + _pm_bp(pm1) - _pm_bp(pm0) + 0.3 * years
    why["sbp"] = "−1 mmHg/kg; alcohol (Roerecke 2017); aerobic −5 (Cornelissen 2013); ARB −10; PM2.5 +1.4 per 10 µg/m³ (Liang 2014)"
    # --- liver fat
    wl_pct = -dw / x0["weight"] * 100
    t["pdff"] = x0["pdff"] * max(0.2, 1 - 0.06 * max(0, wl_pct)) * (1 - 0.2 * min(1, max(0, d("zone2_min_week")) / 150)) * (1 - 0.1 * (d("alcohol_g_week") < -50)) * (1 - 0.3 * glp)
    # --- fitness, autonomic, sleep
    vo2_gain = 0.10 * min(1, max(0, d("zone2_min_week")) / 150) + 0.05 * max(0, d("intervals_per_week")) + (0.03 if quit else 0)
    t["vo2"] = x0["vo2"] * (1 + vo2_gain) * x0["weight"] / t["weight"] - 0.4 * years
    nights = lambda g: min(7, g / 35)  # noqa: E731  ~35 g per drinking night
    t["sleep"] = x0["sleep"] + d("sleep_h") + cal["sleep_per_late_caffeine"] * 3 * ((1 if L.get("late_caffeine") else 0) - (1 if L0.get("late_caffeine") else 0)) / 7 \
        - 0.3 * (nights(L.get("alcohol_g_week") or 0) - nights(L0.get("alcohol_g_week") or 0)) / 7
    t["hrv"] = x0["hrv"] + cal["hrv_per_alcohol_night"] * (nights(L.get("alcohol_g_week") or 0) - nights(L0.get("alcohol_g_week") or 0)) / 7 \
        + cal["hrv_per_sauna"] * d("sauna_per_week") / 7 + cal["hrv_per_sleep_hour"] * (t["sleep"] - x0["sleep"]) + 0.8 * (t["vo2"] - x0["vo2"]) \
        + (5 if quit else 0) - 0.5 * years - 0.4 * (pm1 - pm0) / 10
    t["rhr"] = x0["rhr"] - 0.4 * (t["vo2"] - x0["vo2"]) - (3 if quit else 0) + 0.3 * (nights(L.get("alcohol_g_week") or 0) - nights(L0.get("alcohol_g_week") or 0))
    return t, why


def _pm_bp(pm: float) -> float:
    """SBP from long-term PM2.5: +1.4 mmHg per 10 µg/m³ up to 35 µg/m³, flattening above (Liang 2014; GEMM, Burnett 2018)."""
    return 0.14 * min(pm, 35) + 0.05 * max(0, pm - 35)


def bmd_rate(L: dict, years: float, sex: str) -> float:
    """Spine T-score change per year (≈ 1 SD per 10–12 % BMD)."""
    age = (engine.age_on() or 40) + years
    r = -0.02 if age < 40 else -0.045 if sex == "male" or age < 50 else -0.09
    r -= 0.015 * min(1, (L.get("cig_per_day") or 0) / 10)
    r -= 0.015 * ((L.get("alcohol_g_week") or 0) > 210)
    r += 0.06 * min(1, (L.get("strength_per_week") or 0) / 3) * (1 if years < 2 else 0.3)
    return r


# ----------------------------------------------------------------------------- simulation

def _risk(x: dict, L: dict, years: float) -> dict:
    p = engine.profile()
    age = (engine.age_on() or 40) + years
    h = (p.get("height_cm") or 175) / 100
    tc = x["_tc"] + (x["ldl"] - x["_ldl0"]) + (x["hdl"] - x["_hdl0"]) + (x["tg"] - x["_tg0"]) / 5
    pv = predict.prevent(age, p.get("sex", "male"), tc, x["hdl"], x["sbp"], bool(L.get("telmisartan")), L.get("statin", "none") != "none",
                         x["hba1c"] >= 6.5, (L.get("cig_per_day") or 0) > 0, x["_egfr"] - 0.8 * years, x["weight"] / h / h)
    ph = engine.phenoage({"albumin": x["_albumin"], "creatinine": x["_creatinine"], "glucose": x["glucose"], "hscrp": x["hscrp"], "lymph_pct": x["_lymph_pct"],
                          "mcv": x["_mcv"], "rdw": x["_rdw"], "alp": x["_alp"], "wbc": x["_wbc"]}, age)
    return {"prevent_10y": (pv.get("ten_year") or {}).get("total_cvd"), "prevent_30y": (pv.get("thirty_year") or {}).get("total_cvd"),
            "phenoage": ph.get("value"), "age": round(age, 1)}


def simulate(changes: dict | None = None, years: float = 5) -> dict:
    x0 = state_now()
    L0 = inputs_now()
    L = {**L0, **(changes or {})}
    cal = calibration()
    sex = engine.profile().get("sex", "male")
    for k in ("ldl", "hdl", "tg"):
        x0[f"_{k}0"] = x0[k]

    def run(Lx):
        x = dict(x0)
        traj = {k: [] for k in STATE}
        risk = []
        t, last_whys = 0.0, {}
        horizon = years * 365
        every = max(7, horizon / 40)  # ~40 points per trajectory, always including the final day
        next_rec = 0.0
        while True:
            tgt, why = targets(x0, L0, Lx, cal, t / 365)
            last_whys = why
            if t >= next_rec - 1e-6 or t >= horizon - 1e-6:
                for k in STATE:
                    traj[k].append((round(t), round(x[k], 2)))
                risk.append((round(t), _risk(x, Lx, t / 365)))
                next_rec += every
            if t >= horizon - 1e-6:
                break
            dt = min(1 if t < 120 else 7 if t < 730 else 30, horizon - t)
            for k, (_, _, tau, _) in STATE.items():
                if tau:
                    x[k] += (tgt[k] - x[k]) * (1 - math.exp(-dt / tau))
            x["bmd_t"] += bmd_rate(Lx, t / 365, sex) * dt / 365
            t += dt
        return traj, risk, last_whys

    base, base_risk, _ = run(L0)
    scen, scen_risk, why = run(L) if changes else (base, base_risk, {})
    out = []
    for k, (label, unit, tau, lower) in STATE.items():
        b_end, s_end = base[k][-1][1], scen[k][-1][1]
        out.append({"key": k, "label": label, "unit": unit, "now": round(x0[k], 2), "baseline_end": b_end, "scenario_end": s_end,
                    "difference": round(s_end - b_end, 2), "better": (s_end < b_end) == lower if abs(s_end - b_end) > 1e-6 else None,
                    "baseline": base[k], "scenario": scen[k], "why": why.get(k)})
    unc = 0.25 if not changes or set(changes) <= {"statin", "ezetimibe", "telmisartan", "vitd_iu", "omega3_g"} else 0.45
    return {"years": years, "changes": changes or {}, "inputs_now": L0, "inputs_scenario": L, "calibration": cal, "variables": out,
            "risk_baseline": base_risk, "risk_scenario": scen_risk, "uncertainty": unc,
            "headline": _headline(out, base_risk[-1][1], scen_risk[-1][1], years, changes),
            "disclaimer": "Projection from published effect sizes + your own calibration. Decision aid, not a diagnosis; real response varies (±{:.0%}).".format(unc)}


def _headline(out, rb, rs, years, changes) -> list[str]:
    if not changes:
        return [f"If nothing changes, in {years:g} years: PREVENT 10-y CVD {rb['prevent_10y']}%, PhenoAge {rb['phenoage']} at age {rb['age']}."]
    lines = [f"In {years:g} years: PhenoAge {rb['phenoage']} → {rs['phenoage']} (age {rs['age']}); PREVENT 30-y CVD {rb['prevent_30y']}% → {rs['prevent_30y']}%."]
    for v in sorted(out, key=lambda v: -abs(v["difference"]) / (abs(v["baseline_end"]) + 1e-6))[:5]:
        if abs(v["difference"]) / (abs(v["baseline_end"]) + 1e-6) > 0.02:
            lines.append(f"{v['label']}: {round(v['baseline_end'], 1):g} → {round(v['scenario_end'], 1):g} {v['unit']}")
    return lines


# ----------------------------------------------------------------------------- 24-hour twin

def day(drinking: bool = False, date_: str | None = None) -> dict:
    """Hour by hour: caffeine, nicotine and blood alcohol from today's routine, and what that predicts for tonight."""
    from . import routine
    r = routine.today(date_, drinking)
    cal = calibration()
    w = state_now()["weight"]
    doses = {"caffeine": [], "nicotine": [], "alcohol": []}
    to_h = lambda s: int(s[:2]) + int(s[3:5]) / 60 if s else None  # noqa: E731
    anchors = {"after waking": 8.6, "after lunch": 13.6}
    for it in r["items"]:
        h = to_h(it.get("time")) if it.get("time") else anchors.get(it.get("anchor"))
        if h is None and it["kind"] == "alcohol":
            h = 20.0  # an evening drink with no stated time
        if h is None:
            continue
        if h < 5:
            h += 24
        if it["kind"] == "caffeine":
            doses["caffeine"].append((h, 95))
        if it["kind"] == "smoke":
            for i in range(int(round(it.get("count", 1)))):
                doses["nicotine"].append((h + 0.7 * i, 1.0))
        if it["kind"] == "alcohol" and drinking:
            doses["alcohol"].append((h, it.get("grams_alcohol", 30)))
    wake_it = next((i for i in r["items"] if i["kind"] == "wake" and i.get("time")), None)
    start = max(10, min(18, int(to_h(wake_it["time"]) * 2))) if wake_it else 14  # from wake-up (05:00–09:00), else 07:00
    hours = [h / 2 for h in range(start, start + 44)]  # 22 h, through the night
    caf = [round(sum(dz * 0.5 ** ((t - t0) / 5) for t0, dz in doses["caffeine"] if t >= t0), 1) for t in hours]
    nic = [round(sum(dz * 0.5 ** ((t - t0) / 2) for t0, dz in doses["nicotine"] if t >= t0), 2) for t in hours]
    bac = []
    for t in hours:
        g = sum(dz for t0, dz in doses["alcohol"] if t >= t0 + 0.5)
        start = min((t0 for t0, _ in doses["alcohol"]), default=None)
        bac.append(round(max(0.0, g / (0.68 * w * 1000) * 100 - 0.015 * max(0, t - (start or t) - 0.5)), 3) if g else 0.0)
    sleep_item = next((i for i in r["items"] if i["kind"] == "sleep"), None)
    bed = to_h(sleep_item["time"]) if sleep_item and sleep_item.get("time") else 23.5
    bed = bed + 24 if bed < 5 else bed
    caf_bed = next((c for t, c in zip(hours, caf) if t >= bed), 0)
    base_hrv = state_now()["hrv"]
    hrv = base_hrv + (cal["hrv_per_alcohol_night"] if drinking else 0) - 0.4 * len(doses["nicotine"])
    sleep_h = state_now()["sleep"] - 0.004 * caf_bed - (0.3 if drinking else 0)
    return {"day": r["day"], "drinking": drinking, "hours": hours, "has_routine": bool(r["items"]), "caffeine_mg": caf, "nicotine_mg": nic, "bac_pct": bac,
            "bedtime": f"{int(bed) % 24:02d}:{int((bed % 1) * 60):02d}", "caffeine_at_bed_mg": caf_bed, "peak_bac": max(bac) if bac else 0,
            "tonight": {"hrv": round(hrv, 1), "sleep_h": round(sleep_h, 1), "hrv_baseline": round(base_hrv, 1)},
            "notes": [f"≈ {caf_bed:.0f} mg caffeine still active at bedtime (half-life ~5 h)."] +
                     ([f"{len(doses['nicotine'])} cigarettes → nicotine peaks raise heart rate 10–20 bpm for ~30 min each."] if doses["nicotine"] else []) +
                     ([f"Peak blood alcohol ≈ {max(bac):.3f} % (Widmark); your HRV falls ≈ {abs(cal['hrv_per_alcohol_night']):.0f} ms on drinking nights."] if drinking else []),
            "method": "Caffeine t½ 5 h, nicotine t½ 2 h, Widmark alcohol (r = 0.68, β = 0.015 %/h); tonight from your own measured effects."}


# ----------------------------------------------------------------------------- mirror (fidelity)

def mirror() -> dict:
    """How well does the twin track the real you? (1) nightly HRV replayed from logged events; (2) lab changes July → October."""
    import numpy as np
    cal = calibration()
    hrv = engine.series("hrv")
    sl = dict(engine.series("sleep_hours"))
    tab = {(r["event"], r["metric"]): r["effect"] for r in engine.effect_table()}
    ev = {}
    for e in db.rows("SELECT ts, kind FROM events"):
        ev.setdefault(e["ts"][:10], set()).add(e["kind"])
    base = engine.signal_baseline("hrv", days=120)["mean"]
    pred, act = [], []
    for d, v in hrv:
        prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
        p = base + sum(tab.get((k, "hrv"), 0) for k in ev.get(prev, ())) + cal["hrv_per_sleep_hour"] * ((sl.get(d) or 7) - 7)
        pred.append(p)
        act.append(v)
    pred, act = np.array(pred), np.array(act)
    r2 = 1 - float(((act - pred) ** 2).sum()) / float(((act - act.mean()) ** 2).sum())
    mae = float(np.abs(act - pred).mean())
    labs = []
    for k, mid in (("ldl", "ldl"), ("apob", "apob"), ("hba1c", "hba1c"), ("tg", "tg"), ("vitd", "vitd"), ("hscrp", "hscrp")):
        h = [x for x in engine.marker_history(mid) if x["value_num"] is not None]
        if len(h) >= 2:
            a, b = h[0], h[-1]
            days = (date.fromisoformat(b["collected_on"]) - date.fromisoformat(a["collected_on"])).days
            # twin replay: vitamin D from the supplement start; others = no logged lever change → expect stable
            exp_v = a["value_num"]
            if mid == "vitd":
                exp_v = a["value_num"] + cal["vitd_response"] * 20 * (1 - math.exp(-days / 25))
            err = b["value_num"] - exp_v
            labs.append({"marker": STATE[k][0], "from": a["value_num"], "to": b["value_num"], "twin_expected": round(exp_v, 1), "unexplained": round(err, 1),
                         "unexplained_pct": round(100 * err / exp_v, 1),
                         "comment": "tracked" if abs(err) / exp_v < 0.08 else "drifted more than your logged life explains — a missing input (illness, diet change, sleep, stress) worth finding"})
    return {"hrv": {"r2": round(r2, 2), "mae_ms": round(mae, 1), "nights": len(act),
                    "series": [{"day": d, "actual": a, "twin": round(float(p), 1)} for (d, a), p in zip(hrv[-45:], pred[-45:])]},
            "labs": labs, "calibration": cal,
            "fidelity": round(max(0.0, min(1.0, 0.6 * max(0, r2) + 0.4 * (1 - min(1, float(np.mean([abs(x['unexplained_pct']) for x in labs]) / 25 if labs else 1))))), 2)}


def overview() -> dict:
    x = state_now()
    L = inputs_now()
    cal = calibration()
    now_risk = _risk({**x, "_ldl0": x["ldl"], "_hdl0": x["hdl"], "_tg0": x["tg"]}, L, 0)
    systems = [
        ("Heart & vessels", ["ldl", "apob", "hdl", "tg", "sbp", "hscrp"]), ("Metabolism", ["hba1c", "glucose", "weight", "vat", "pdff"]),
        ("Muscle & bone", ["lean_kg", "almi", "fat_kg", "bmd_t"]), ("Fitness & recovery", ["vo2", "hrv", "rhr", "sleep"]), ("Nutrients", ["vitd", "omega3"]),
    ]
    return {"inputs": L, "levers": {k: {"label": v[0], "kind": v[1], "options": v[2]} for k, v in LEVERS.items()},
            "presets": [{"id": k, "label": v[0], "changes": v[1]} for k, v in PRESETS.items()],
            "systems": [{"name": n, "variables": [{"key": k, "label": STATE[k][0], "unit": STATE[k][1], "value": round(x[k], 2)} for k in ks]} for n, ks in systems],
            "risk_now": now_risk, "calibration": cal,
            "about": "Your twin runs your logged routine, meals, alcohol, cigarettes, supplements, medicines, therapies, sleep, training and city through "
                     "published physiology, calibrated to how your own body has responded."}
