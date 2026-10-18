"""Telomy synthetic cohort — 100 fictional people with full lives and PLANTED ground truth, each run through the whole
Telomy backend in an isolated database, then scored: do the engines rediscover what we planted, and nothing else?

SYNTHETIC ONLY. Every profile is flagged is_test_profile / is_synthetic; nothing here is a real person, nothing is
written to the real database, and none of it may ever be shown as a user's data or stored in a Vault.

Per person (deterministic from the cohort seed + person id):
  demographics, BMI, conditions (hypertension, prediabetes/T2D, dyslipidaemia, hypothyroid, iron deficiency, sleep
  apnoea, anxiety), smoking, habits (alcohol, late meals, late caffeine, sauna, cold plunge, hard training, steps),
  chronotype, medications/supplements consistent with conditions, two lab reports consistent with physiology,
  120 days of daily wearable signals, events, moods, symptoms, meals, therapy sessions.
  PLANTED EFFECTS with person-specific magnitudes; ~20 % of habits deliberately have NO effect (true negatives).
usage:  python -m sim.cohort build  --people 100 --out ~/telomy-lab/cohort/run1
        python -m sim.cohort eval   --out ~/telomy-lab/cohort/run1
        python -m sim.cohort advance --out ~/telomy-lab/cohort/run1     (adds one more day to everyone, for daily runs)
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Ananya", "Vikram", "Isha", "Arjun", "Sara", "Neel", "Tara", "Dev",
         "Riya", "Karan", "Zoya", "Aditya", "Nisha", "Farhan", "Leela"]
CONDITIONS = {  # prevalence, effect on physiology
    "hypertension": 0.22, "prediabetes": 0.18, "type2_diabetes": 0.08, "dyslipidaemia": 0.25, "hypothyroid": 0.08,
    "iron_deficiency": 0.10, "sleep_apnoea": 0.10, "anxiety": 0.12,
}
HABITS = ["alcohol", "late_meal", "caffeine_late", "sauna", "cold_plunge", "workout_hard"]


def persona(i: int, seed: int) -> dict:
    r = random.Random(seed * 100003 + i)
    sex = r.choice(["male", "female"])
    age = int(min(78, max(19, r.gauss(42, 13))))
    bmi = round(min(42, max(17.5, r.gauss(25.5 + 0.05 * (age - 40), 4.2))), 1)
    cond = {c for c, p in CONDITIONS.items() if r.random() < p * (1.6 if age > 50 else 0.8) * (1.4 if bmi > 29 and c in ("hypertension", "prediabetes", "type2_diabetes", "dyslipidaemia", "sleep_apnoea") else 1)}
    if "type2_diabetes" in cond:
        cond.discard("prediabetes")
    fit = r.gauss(0, 1) - 0.04 * (bmi - 25)
    habits = {
        "alcohol_per_week": max(0, round(r.choice([0, 0, 1, 2, 3, 5, 8]) + r.gauss(0, 0.5))),
        "late_meal_p": round(r.uniform(0.0, 0.3), 2), "caffeine_late_p": round(r.uniform(0.0, 0.25), 2),
        "sauna_per_week": r.choice([0, 0, 0, 1, 2, 3]), "cold_per_week": r.choice([0, 0, 0, 1, 2]),
        "hard_per_week": r.choice([0, 1, 2, 3, 4]), "steps_mean": int(max(2500, r.gauss(7500 + 1800 * fit, 2200))),
        "smoker": r.random() < 0.12, "bedtime_h": round(r.gauss(23.4, 0.8), 2), "sleep_need_h": round(min(9, max(6.5, r.gauss(7.6, 0.4))), 2),
    }
    # planted effects (next day); 0 = true negative. Magnitudes person-specific, realistic ranges from the literature.
    def eff(lo, hi, p_zero=0.2):
        return 0.0 if r.random() < p_zero else round(r.uniform(lo, hi), 2)
    effects = {
        "alcohol": {"hrv": eff(-14, -4), "rhr": eff(1.5, 5), "deep_sleep": eff(-0.4, -0.1)},
        "late_meal": {"deep_sleep": eff(-0.45, -0.1), "sleep_score": eff(-9, -3)},
        "caffeine_late": {"sleep_hours": eff(-0.7, -0.2)},
        "sauna": {"deep_sleep": eff(0.1, 0.35), "hrv": eff(1.5, 6)},
        "cold_plunge": {"hrv": eff(1, 5)},
        "workout_hard": {"hrv": eff(-9, -3)},
    }
    hrv0 = math.exp(math.log(58) - 0.016 * (age - 30) + 0.12 * fit + r.gauss(0, 0.18)) * (0.85 if "anxiety" in cond else 1) * (0.9 if "type2_diabetes" in cond else 1)
    rhr0 = 66 - 4 * fit + (3 if "hypertension" in cond else 0) + (2 if habits["smoker"] else 0) + r.gauss(0, 3)
    meds = []
    if "hypertension" in cond: meds.append(("Telmisartan", "40 mg", "daily", ["08:00"], "Blood pressure"))
    if "type2_diabetes" in cond: meds.append(("Metformin", "500 mg", "twice daily", ["08:00", "20:00"], "Type 2 diabetes"))
    if "dyslipidaemia" in cond and r.random() < 0.5: meds.append(("Rosuvastatin", "10 mg", "daily", ["21:00"], "Cholesterol"))
    if "hypothyroid" in cond: meds.append(("Levothyroxine", "50 mcg", "daily", ["07:00"], "Hypothyroidism"))
    if "iron_deficiency" in cond: meds.append(("Ferrous ascorbate", "100 mg", "daily", ["13:00"], "Iron deficiency"))
    if r.random() < 0.35: meds.append(("Vitamin D3", "2000 IU", "daily", ["09:00"], "Supplement"))
    return {"id": i, "synthetic": True, "first_name": FIRST[i % len(FIRST)], "name": f"Sim {i:03d}", "sex": sex, "age": age,
            "dob": f"{2026 - age}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}", "height_cm": round(r.gauss(172 if sex == "male" else 159, 7)),
            "bmi": bmi, "conditions": sorted(cond), "fitness_z": round(fit, 2), "habits": habits, "effects": effects,
            "baseline": {"hrv": round(hrv0, 1), "rhr": round(rhr0, 1), "vo2max": round(max(22, 44 - 0.3 * (age - 30) + 5 * fit - 0.4 * (bmi - 25)), 1)},
            "meds": meds, "devices": r.choice([["ring"], ["ring", "patch"], ["watch"], ["ring", "watch"], ["whoop"], ["patch"]])}


def labs_for(p: dict, r: random.Random, months_ago: int) -> dict:
    c = set(p["conditions"]); bmi = p["bmi"]; drift = 0.97 if months_ago > 2 else 1.0
    g = lambda m, s: round(r.gauss(m, s), 1)  # noqa: E731
    hba1c = g(6.9 if "type2_diabetes" in c else 5.9 if "prediabetes" in c else 5.25 + 0.02 * (bmi - 25), 0.2)
    ldl = g(158 if "dyslipidaemia" in c else 105, 18) * drift
    v = {"glucose": g(140 if "type2_diabetes" in c else 108 if "prediabetes" in c else 88 + 0.6 * (bmi - 25), 7),
         "hba1c": hba1c, "insulin": g(14 if bmi > 29 or "prediabetes" in c else 6.5, 2.5), "chol_total": round(ldl + g(65, 10)),
         "ldl": round(ldl), "hdl": g(38 if bmi > 29 else 52 if p["sex"] == "male" else 60, 7), "tg": g(190 if "dyslipidaemia" in c or bmi > 29 else 105, 30),
         "apob": g(118 if "dyslipidaemia" in c else 85, 12), "hscrp": round(abs(r.gauss(3.2 if bmi > 29 or p["habits"]["smoker"] else 1.0, 0.8)), 2),
         "alt": g(48 if bmi > 30 else 26, 8), "ast": g(30, 6), "creatinine": round(r.gauss(1.0 if p["sex"] == "male" else 0.8, 0.12), 2),
         "tsh": g(6.8 if "hypothyroid" in c else 2.1, 0.8), "vitd": g(32 if any("Vitamin D" in m[0] for m in p["meds"]) else 19, 6),
         "b12": round(r.gauss(420, 120)), "ferritin": g(12 if "iron_deficiency" in c else 95 if p["sex"] == "male" else 55, 6 if "iron_deficiency" in c else 25),
         "hemoglobin": g(10.9 if "iron_deficiency" in c else 14.8 if p["sex"] == "male" else 13.0, 0.6),
         "uric_acid": g(6.6 if bmi > 29 else 5.1, 0.8), "egfr": round(max(45, r.gauss(110 - 0.8 * (p["age"] - 30), 10)))}
    return {k: max(0.1, val) for k, val in v.items()}


def build_one(p: dict, db_path: str, days: int, today: date):
    """Write one person into an isolated DB through the backend's own tables (same shapes the app writes)."""
    os.environ["TELOMY_DB"] = db_path
    sys.path.insert(0, ROOT)
    from app import catalog, db  # noqa: E402
    db.DB_PATH = db_path
    db.init(reset=True)
    for mod in ("roles", "plans", "therapy", "rx", "summaries", "voice", "routine", "activities", "exposome", "devices", "band", "whoop"):
        try:
            __import__(f"app.{mod}", fromlist=["init"]).init()
        except Exception:  # noqa: BLE001 — optional modules
            pass
    r = random.Random(p["id"] * 7919)
    h, e, b = p["habits"], p["effects"], p["baseline"]
    db.exec_("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)", (db.j({
        "name": p["name"], "first_name": p["first_name"], "dob": p["dob"], "sex": p["sex"], "height_cm": p["height_cm"],
        "goal": "Synthetic cohort member", "smoker": h["smoker"], "bp_treated": "hypertension" in p["conditions"],
        "family_history_dm": r.random() < 0.3, "conditions": p["conditions"], "is_test_profile": True, "is_synthetic": True, "onboarded": True}),))
    start = today - timedelta(days=days - 1)
    did = {k: set() for k in HABITS}
    for i in range(days):
        d = start + timedelta(days=i); wd = d.weekday()
        def ev(kind, label, hour, sev=None):
            db.exec_("INSERT INTO events (ts, kind, label, severity, data, source) VALUES (?,?,?,?,?,?)",
                     (f"{d.isoformat()}T{hour:02d}:{r.randint(0, 59):02d}:00", kind, label, sev, db.j({"synthetic": True}), "sim"))
        if r.random() < h["alcohol_per_week"] / 7 * (1.6 if wd in (4, 5) else 0.8): did["alcohol"].add(d); ev("alcohol", "2 drinks", 21)
        if r.random() < h["late_meal_p"]: did["late_meal"].add(d); ev("late_meal", "Dinner after 11 pm", 23)
        if r.random() < h["caffeine_late_p"]: did["caffeine_late"].add(d); ev("caffeine_late", "Coffee at 5 pm", 17)
        if r.random() < h["sauna_per_week"] / 7: did["sauna"].add(d); ev("sauna", "Sauna 20 min", 18)
        if r.random() < h["cold_per_week"] / 7: did["cold_plunge"].add(d); ev("cold_plunge", "Cold plunge 3 min", 7)
        if r.random() < h["hard_per_week"] / 7: did["workout_hard"].add(d); ev("workout_hard", "Hard training session", 7)
        if r.random() < 0.5: ev("mood", r.choice(["Low", "Okay", "Good", "Great"]), 22, r.randint(2, 5))
        if r.random() < (0.12 if "anxiety" in p["conditions"] else 0.05): ev("stress", "Stressful day", 19)
        if r.random() < 0.05: ev("symptom", r.choice(["Headache", "Fatigue", "Bloating"]), 15, r.randint(1, 3))
    for i in range(days):
        d = start + timedelta(days=i); prev = d - timedelta(days=1)
        hit = {k: prev in did[k] for k in HABITS}
        add = lambda metric: sum(e[k].get(metric, 0) for k in HABITS if hit[k])  # noqa: E731
        steps = max(800, r.gauss(h["steps_mean"] * (0.8 if d.weekday() >= 5 else 1), 2000))
        sleep_h = max(3.8, min(10, r.gauss(h["sleep_need_h"] - 0.5, 0.6) + add("sleep_hours") - (0.4 if "sleep_apnoea" in p["conditions"] else 0)))
        deep = max(0.3, min(2.6, 1.4 - 0.012 * (p["age"] - 30) + 0.05 * (steps - 7000) / 1000 + 0.08 * (sleep_h - 7) + add("deep_sleep") + r.gauss(0, 0.13)))
        rem = max(0.5, r.gauss(1.7, 0.25) + 0.1 * (sleep_h - 7))
        hrv = max(8, b["hrv"] + 4 * (sleep_h - 7) + add("hrv") + r.gauss(0, b["hrv"] * 0.09))
        rhr = b["rhr"] - 0.1 * (hrv - b["hrv"]) + add("rhr") + r.gauss(0, 1.5)
        score = max(25, min(98, 64 + 9 * (sleep_h - 7) + 14 * (deep - 1.2) + add("sleep_score") + r.gauss(0, 4)))
        vals = {"steps": round(steps), "exercise_min": round(55 if d in did["workout_hard"] else max(0, r.gauss(22, 14))),
                "sleep_hours": round(sleep_h, 2), "deep_sleep": round(deep, 2), "rem_sleep": round(rem, 2), "sleep_score": round(score),
                "hrv": round(hrv, 1), "rhr": round(rhr, 1), "vo2max": b["vo2max"], "weight": round(p["bmi"] * (p["height_cm"] / 100) ** 2 + r.gauss(0, 0.3), 1),
                "resp_rate": round(r.gauss(14.5 + (1.2 if "sleep_apnoea" in p["conditions"] else 0), 0.6), 1),
                "spo2": round(min(99, r.gauss(93.5 if "sleep_apnoea" in p["conditions"] else 96.5, 0.8)), 1)}
        for k, v in vals.items():
            db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (d.isoformat(), k, v, "sim"))
    for months_ago in (4, 0):
        vals = labs_for(p, r, months_ago)
        day = (today - timedelta(days=30 * months_ago + 5)).isoformat()
        rid = db.exec_("INSERT INTO reports (title, panel, collected_on, source, filename, is_test_data) VALUES (?,?,?,?,?,?)",
                       ("Synthetic blood panel", "blood", day, "sim", f"sim_{p['id']:03d}_{months_ago}.pdf", 1))
        for mid, v in vals.items():
            spec = catalog.MARKERS[mid]
            db.exec_("""INSERT INTO results (report_id, marker_id, value_num, unit, status, note) VALUES (?,?,?,?,?,?)""",
                     (rid, mid, v, spec[2], catalog.status_for(mid, v), "synthetic"))
    for name, dose, freq, times, why in p["meds"]:
        try:
            db.exec_("INSERT INTO medications (name, dose, frequency, times, reason, prescriber, start_day, active, source) VALUES (?,?,?,?,?,?,?,?,?)",
                     (name, dose, freq, db.j(times), why, "Synthetic clinician", (start - timedelta(days=200)).isoformat(), 1, "sim"))
        except Exception:  # noqa: BLE001 — schema differences tolerated
            pass
    json.dump({"planted": {k: sorted(x.isoformat() for x in v) for k, v in did.items()}}, open(db_path + ".truth.json", "w"))


def cmd_build(a):
    out = os.path.expanduser(a.out); os.makedirs(out, exist_ok=True)
    today = date.fromisoformat(a.today)
    people = [persona(i, a.seed) for i in range(a.people)]
    json.dump(people, open(f"{out}/people.json", "w"), indent=1)
    for p in people:
        db_path = f"{out}/p{p['id']:03d}.db"
        subprocess.run([sys.executable, "-m", "sim.cohort", "_one", "--out", out, "--id", str(p["id"]), "--days", str(a.days), "--today", a.today],
                       cwd=ROOT, check=True)
    print(f"built {len(people)} people → {out}")


def cmd_one(a):
    out = os.path.expanduser(a.out)
    p = next(x for x in json.load(open(f"{out}/people.json")) if x["id"] == a.id)
    build_one(p, f"{out}/p{p['id']:03d}.db", a.days, date.fromisoformat(a.today))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "_one", "eval"])
    ap.add_argument("--out", default="~/telomy-lab/cohort/run1"); ap.add_argument("--people", type=int, default=100)
    ap.add_argument("--days", type=int, default=120); ap.add_argument("--seed", type=int, default=20261019)
    ap.add_argument("--today", default=date.today().isoformat()); ap.add_argument("--id", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "build": cmd_build(a)
    elif a.cmd == "_one": cmd_one(a)
    else:
        from sim import evaluate
        evaluate.run(os.path.expanduser(a.out))


if __name__ == "__main__":
    main()
