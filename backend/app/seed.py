"""Seed a realistic TEST profile: 120 days of wearable data with embedded causal effects, events, meals,
protocols, clinicians, consents and the 7 dummy lab reports ingested through the real parser.

Embedded ground truth (so the correlation engine can be verified):
  alcohol        → next night HRV −9 ms, RHR +4, deep sleep −0.30 h, sleep score −7
  late meal      → deep sleep −0.35 h, sleep score −6
  sauna          → deep sleep +0.25 h, HRV +4
  hard workout   → next-day HRV −6
  caffeine late  → sleep −0.45 h
  steps          → deep sleep (+0.06 h per 1k steps above 7k)
  sleep hours    → same-night HRV (+4 ms per hour)
  magnesium N-of-1 (ABAB, 7-day periods from 2026-08-25) → deep sleep +0.22 h on B periods
  last 35 days   → HRV drifts −6 ms (matches hs-CRP rise between July and October)
"""
import glob
import os
import random
from datetime import date, datetime, timedelta

from . import db, engine
from .labparse import parse_pdf

TODAY = date.fromisoformat(os.environ.get("TELOMY_TODAY", date.today().isoformat()))
DAYS = 120
TESTDATA = os.path.join(os.path.dirname(__file__), "..", "..", "testdata", "lab_reports")


def save_report(parsed: dict, source: str, filename: str) -> int:
    rid = db.exec_("INSERT INTO reports (title, panel, collected_on, source, filename, is_test_data) VALUES (?,?,?,?,?,?)",
                   (parsed["title"], parsed["panel"], parsed["collected_on"], source, filename,
                    1 if parsed.get("is_test_data") else 0))
    for m in parsed["markers"]:
        num = m["value"] if isinstance(m["value"], (int, float)) else None
        db.exec_("""INSERT INTO results (report_id, marker_id, value_num, value_text, unit, ref_low, ref_high, ref_text,
                    flag, status, note) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                 (rid, m["marker_id"], num, None if num is not None else str(m["value"]), m["unit"], m["ref_low"],
                  m["ref_high"], m.get("ref_text"), m.get("flag"), m["status"], m.get("note")))
    return rid


def run(reset=True):
    db.init(reset=reset)
    rnd = random.Random(42)
    start = TODAY - timedelta(days=DAYS - 1)

    db.exec_("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)", (db.j({
        "name": "Test User", "first_name": "Aarav", "dob": "1992-07-15", "sex": "male", "height_cm": 178,
        "phone": "+91 90000 00000", "goal": "Track biomarkers and sleep better", "city": "Bengaluru",
        "emergency": {"blood_type": "B+", "allergies": "Penicillin", "conditions": "None known",
                      "medications": "Vitamin D3 2000 IU", "contact": "Test Contact · +91 90000 00001"},
        "is_test_profile": True, "onboarded": True, "smoker": False, "bp_treated": False, "family_history_dm": True}),))

    # ---- events
    events = []
    def ev(d, kind, label, hour=21, severity=None, data=None):
        events.append((f"{d.isoformat()}T{hour:02d}:{rnd.randint(0, 59):02d}:00", kind, label, severity, data))

    alcohol_days, late_meal_days, sauna_days, hard_days, caff_days = set(), set(), set(), set(), set()
    for i in range(DAYS):
        d = start + timedelta(days=i)
        wd = d.weekday()
        if (wd in (4, 5) and rnd.random() < 0.55) or rnd.random() < 0.04:
            alcohol_days.add(d); ev(d, "alcohol", rnd.choice(["2 glasses red wine", "2 beers", "Whisky 60 ml"]), 21)
        if rnd.random() < 0.13:
            late_meal_days.add(d); ev(d, "late_meal", "Dinner at 11 pm", 23)
        if wd in (1, 6) and rnd.random() < 0.7:
            sauna_days.add(d); ev(d, "sauna", "Sauna 20 min, 80 °C", 18)
        if wd in (0, 3) and rnd.random() < 0.75:
            hard_days.add(d); ev(d, "workout_hard", rnd.choice(["Zone 5 intervals 4×4", "Heavy lower-body session"]), 7)
        if rnd.random() < 0.09:
            caff_days.add(d); ev(d, "caffeine_late", "Coffee at 5 pm", 17)
        if rnd.random() < 0.6:
            mood = rnd.choice([3, 4, 4, 4, 5, 2, 3])
            ev(d, "mood", ["", "Very low", "Low", "Okay", "Good", "Great"][mood], 22, mood,
               db.j({"note": rnd.choice(["", "Long meetings", "Good run", "Slept badly", "Calm day", "Family dinner"])}))
        if rnd.random() < 0.06:
            ev(d, "symptom", rnd.choice(["Headache", "Bloating", "Fatigue", "Acid reflux"]), 15, rnd.randint(1, 3))
        if rnd.random() < 0.07:
            ev(d, "stress", "Deadline at work", 19)
    trip = TODAY - timedelta(days=52)
    for k in range(4):
        ev(trip + timedelta(days=k), "travel", "Work trip to Singapore", 9)
    ev(date(2026, 7, 10), "supplement", "Started Vitamin D3 2000 IU daily", 9, data=db.j({"dose": "2000 IU"}))
    ev(date(2026, 8, 25), "supplement", "Magnesium glycinate 300 mg (N-of-1)", 21, data=db.j({"dose": "300 mg"}))
    ev(TODAY - timedelta(days=40), "life", "Moved to a new apartment", 12)
    ev(TODAY - timedelta(days=18), "hbot", "Halo session 60 min", 10)
    for e in events:
        db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", e)

    # ---- N-of-1 magnesium study (7-day periods ABAB)
    study_start = date(2026, 8, 25)
    def mg_on(d):
        k = (d - study_start).days
        return 0 <= k < 28 and (k // 7) % 2 == 1

    # ---- signals
    vo2 = 42.0
    weight = 81.5
    for i in range(DAYS):
        d = start + timedelta(days=i)
        prev = d - timedelta(days=1)
        wd = d.weekday()
        steps = max(1500, rnd.gauss(9500 if wd < 5 else 7000, 2600))
        if trip <= d < trip + timedelta(days=4):
            steps = rnd.gauss(4200, 800)
        exercise = 55 if d in hard_days else max(0, rnd.gauss(28, 15))
        sleep_h = rnd.gauss(7.0, 0.55) - (0.45 if prev in caff_days else 0) - (0.3 if prev in alcohol_days else 0)
        if trip <= d < trip + timedelta(days=4):
            sleep_h -= 0.8
        sleep_h = max(4.2, min(9.2, sleep_h))
        deep = (1.35 + 0.06 * (steps - 7000) / 1000 + 0.08 * (sleep_h - 7) + rnd.gauss(0, 0.13)
                - (0.30 if prev in alcohol_days else 0) - (0.35 if prev in late_meal_days else 0)
                + (0.25 if prev in sauna_days else 0) + (0.22 if mg_on(d) else 0))
        deep = max(0.4, min(2.6, deep))
        rem = max(0.6, rnd.gauss(1.7, 0.25) + 0.1 * (sleep_h - 7) - (0.2 if prev in alcohol_days else 0))
        drift = -6 * max(0, (i - (DAYS - 35))) / 35
        hrv = (54 + 4 * (sleep_h - 7) + rnd.gauss(0, 5) + drift - (9 if prev in alcohol_days else 0)
               + (4 if prev in sauna_days else 0) - (6 if prev in hard_days else 0))
        rhr = 58 - 0.12 * (hrv - 54) + rnd.gauss(0, 1.6) + (4 if prev in alcohol_days else 0)
        score = max(30, min(98, 62 + 9 * (sleep_h - 7) + 14 * (deep - 1.3) + rnd.gauss(0, 4)
                            - (7 if prev in alcohol_days else 0) - (6 if prev in late_meal_days else 0)))
        daylight = max(5, rnd.gauss(70 if wd >= 5 else 38, 20))
        vo2 += rnd.gauss(0.01, 0.05)
        weight += rnd.gauss(-0.005, 0.15)
        vals = {
            "steps": round(steps), "exercise_min": round(exercise), "active_kcal": round(steps * 0.042 + exercise * 6),
            "sleep_hours": round(sleep_h, 2), "deep_sleep": round(deep, 2), "rem_sleep": round(rem, 2),
            "sleep_score": round(score), "hrv": round(hrv, 1), "rhr": round(rhr, 1),
            "spo2": round(min(99.5, rnd.gauss(96.8, 0.8)), 1), "resp_rate": round(rnd.gauss(14.6, 0.6), 1),
            "skin_temp": round(rnd.gauss(0, 0.18) + (0.35 if prev in alcohol_days else 0), 2),
            "daylight_min": round(daylight), "mindful_min": round(max(0, rnd.gauss(6, 6))),
        }
        if i % 3 == 0:  # home BP cuff every 3 days
            vals["sbp"] = round(rnd.gauss(128, 6) + (5 if prev in alcohol_days else 0))
            vals["dbp"] = round(rnd.gauss(82, 4))
        if i % 7 == 0:
            vals["vo2max"] = round(vo2, 1)
            vals["weight"] = round(weight, 1)
        if i >= DAYS - 14:  # two-week CGM sensor
            vals["glucose_mean"] = round(rnd.gauss(104, 6) + (8 if prev in late_meal_days else 0))
        for k, v in vals.items():
            src = "CGM · Libre" if k == "glucose_mean" else "BP cuff · Omron" if k in ("sbp", "dbp") else "Telomy Band" if k in ("hrv", "rhr", "skin_temp", "spo2",
                  "resp_rate", "deep_sleep", "rem_sleep", "sleep_hours", "sleep_score") else "Apple Health"
            db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)",
                     (d.isoformat(), k, v, src))

    # ---- meals
    meal_names = [("Ragi dosa with tomato chutney", 304, 10, 48, 8, 78), ("Arhar dal, rice and beans sabzi", 520, 22, 78, 12, 72),
                  ("Paneer tikka salad", 410, 32, 14, 24, 86), ("Masala oats with egg", 360, 21, 40, 12, 80),
                  ("Chole with two rotis", 610, 21, 88, 18, 64), ("Grilled fish, quinoa, greens", 480, 42, 36, 16, 91)]
    for k in range(10):
        n, kcal, p, c, f, s = meal_names[k % len(meal_names)]
        ts = datetime.combine(TODAY - timedelta(days=k // 3), datetime.min.time()) + timedelta(hours=8 + 5 * (k % 3))
        db.exec_("INSERT INTO meals (ts, name, analysis) VALUES (?,?,?)", (ts.isoformat(), n, db.j(
            {"kcal": kcal, "protein": p, "carbs": c, "fat": f, "fibre": round(c * 0.12), "score": s, "source": "seed"})))

    # ---- lab reports through the real parser
    for path in sorted(glob.glob(os.path.join(TESTDATA, "*.pdf"))):
        with open(path, "rb") as fh:
            parsed = parse_pdf(fh.read(), os.path.basename(path))
        save_report(parsed, "Sample Diagnostics (test)", os.path.basename(path))

    # ---- N-of-1 study record
    db.exec_("""INSERT INTO studies (title, intervention, outcome, design, start_day, period_days, status, data)
                VALUES (?,?,?,?,?,?,?,?)""",
             ("Does magnesium deepen my sleep?", "Magnesium glycinate 300 mg at night", "deep_sleep", "ABAB",
              study_start.isoformat(), 7, "complete", db.j({"hypothesis": "Magnesium increases deep sleep"})))

    # ---- protocols
    protocols = [
        {"id": "metabolic-reset", "title": "Metabolic reset", "phase": "Phase 1 of 3", "clinician": "Dr. Meera Rao",
         "review": "every 4 weeks", "targets": ["HbA1c < 5.6%", "HOMA-IR < 2", "Triglycerides < 150"],
         "evidence": "B", "author": "Dr. Meera Rao, MD (Endocrinology)",
         "pillars": {
             "Lifestyle": [{"id": "l1", "title": "Morning daylight 15 min", "when": "Daily, before 9 am"},
                           {"id": "l2", "title": "Lights down by 10:30 pm", "when": "Daily"}],
             "Diet": [{"id": "d1", "title": "30 g protein at breakfast", "when": "Daily"},
                      {"id": "d2", "title": "10-minute walk after meals", "when": "After lunch and dinner"},
                      {"id": "d3", "title": "Dinner finished 3 h before bed", "when": "Daily"}],
             "Fitness": [{"id": "f1", "title": "Zone 2 cardio 45 min", "when": "3× per week"},
                         {"id": "f2", "title": "Strength training", "when": "2× per week"}],
             "Supplements": [{"id": "s1", "title": "Vitamin D3 2000 IU", "when": "With breakfast"},
                             {"id": "s2", "title": "Magnesium glycinate 300 mg", "when": "At night"}]}},
        {"id": "sleep-architecture", "title": "Sleep architecture", "phase": "4 weeks", "clinician": "Dr. Arjun Menon",
         "review": "every 2 weeks", "targets": ["Deep sleep ≥ 1.5 h", "Sleep score ≥ 80"], "evidence": "B",
         "author": "Dr. Arjun Menon, MD (Sleep medicine)", "pillars": {
             "Lifestyle": [{"id": "sa1", "title": "Same wake time ±30 min", "when": "Daily"}],
             "Diet": [{"id": "sa2", "title": "No caffeine after 1 pm", "when": "Daily"}],
             "Fitness": [{"id": "sa3", "title": "Sauna 20 min", "when": "2× per week"}],
             "Supplements": []}},
        {"id": "lipid-lowering", "title": "ApoB lowering", "phase": "12 weeks", "clinician": "Dr. Kavya Iyer",
         "review": "every 6 weeks", "targets": ["ApoB < 80 mg/dL"], "evidence": "A",
         "author": "Dr. Kavya Iyer, DM (Cardiology)", "pillars": {
             "Lifestyle": [], "Diet": [{"id": "ll1", "title": "Soluble fibre 10 g (psyllium)", "when": "Daily"},
                                       {"id": "ll2", "title": "Saturated fat under 15 g", "when": "Daily"}],
             "Fitness": [{"id": "ll3", "title": "150 min moderate activity", "when": "Weekly"}], "Supplements": []}},
        {"id": "gut-diversity", "title": "Gut diversity", "phase": "8 weeks", "clinician": "Dr. Meera Rao",
         "review": "every 4 weeks", "targets": ["Shannon > 3.5", "Calprotectin < 50"], "evidence": "C",
         "author": "Dr. Meera Rao, MD", "pillars": {
             "Lifestyle": [], "Diet": [{"id": "g1", "title": "30 different plants per week", "when": "Weekly"},
                                       {"id": "g2", "title": "Fermented food daily (curd, kanji)", "when": "Daily"}],
             "Fitness": [], "Supplements": []}},
    ]
    for p in protocols:
        db.exec_("INSERT INTO protocols (id, data, active) VALUES (?,?,?)", (p["id"], db.j(p), 1 if p["id"] == "metabolic-reset" else 0))

    # ---- clinicians & appointments
    clinicians = [
        {"id": "c1", "name": "Dr. Meera Rao", "title": "MD, Endocrinology", "clinic": "Telomy Care · Indiranagar",
         "rating": 4.9, "years": 14, "modes": ["clinic", "video", "home lab"], "fee": 1500, "next": "Thu 10:30"},
        {"id": "c2", "name": "Dr. Kavya Iyer", "title": "DM, Cardiology", "clinic": "Telomy Care · Koramangala",
         "rating": 4.8, "years": 11, "modes": ["clinic", "video"], "fee": 2000, "next": "Fri 16:00"},
        {"id": "c3", "name": "Dr. Arjun Menon", "title": "MD, Sleep medicine", "clinic": "Telomy Care · HSR",
         "rating": 4.7, "years": 9, "modes": ["video"], "fee": 1200, "next": "Today 18:30"},
        {"id": "c4", "name": "Dr. Sana Qureshi", "title": "MD, Gastroenterology", "clinic": "Telomy Care · Whitefield",
         "rating": 4.8, "years": 12, "modes": ["clinic", "video"], "fee": 1800, "next": "Mon 11:00"},
    ]
    for c in clinicians:
        db.exec_("INSERT INTO clinicians (id, data) VALUES (?,?)", (c["id"], db.j(c)))
    db.exec_("INSERT INTO appointments (clinician_id, ts, kind, status, reason) VALUES (?,?,?,?,?)",
             ("c2", (datetime.combine(TODAY + timedelta(days=3), datetime.min.time()) + timedelta(hours=16)).isoformat(),
              "clinic", "confirmed", "Lipids and ApoB review"))

    # ---- consents (default off; a few granted with history)
    now = engine.now_iso()
    purposes = ["wearable_sync", "lab_analysis", "sinc_ai", "clinician_sharing", "research", "family_sharing",
                "cycle_tracking", "marketing"]
    granted = {"wearable_sync", "lab_analysis", "sinc_ai", "clinician_sharing"}
    for p in purposes:
        db.exec_("INSERT INTO consents (purpose, granted, updated_at) VALUES (?,?,?)", (p, 1 if p in granted else 0, now))
        if p in granted:
            db.exec_("INSERT INTO consent_history (purpose, granted, ts) VALUES (?,?,?)", (p, 1, now))

    # ---- family vault share, memories, imaging
    db.exec_("INSERT INTO shares (name, relation, scopes, expires_on, status, created_at) VALUES (?,?,?,?,?,?)",
             ("Test Spouse", "Spouse", db.j(["sleep", "activity"]), (TODAY + timedelta(days=60)).isoformat(), "active", now))
    db.exec_("INSERT INTO access_log (ts, who, what) VALUES (?,?,?)", (now, "Test Spouse", "Viewed sleep summary"))
    for f in ["Prefers vegetarian meals on weekdays", "Trains in the mornings", "Wants to avoid statins if possible",
              "Takes Vitamin D3 2000 IU"]:
        db.exec_("INSERT INTO memories (ts, fact, source) VALUES (?,?,?)", (now, f, "Sinc chat"))
    db.exec_("INSERT INTO imaging (data) VALUES (?)", (db.j({
        "title": "Carotid ultrasound (CIMT)", "modality": "US", "day": "2026-08-02", "series": 2, "images": 48,
        "findings": [{"text": "Mean CIMT 0.62 mm, right; 0.65 mm, left", "status": "in_range"},
                     {"text": "No plaque identified", "status": "optimal"}],
        "radiologist": "Test Radiologist, MD", "is_test_data": True}),))
    db.exec_("INSERT INTO imaging (data) VALUES (?)", (db.j({
        "title": "DEXA body composition", "modality": "DXA", "day": "2026-07-20", "series": 1, "images": 3,
        "findings": [{"text": "Body fat 24.1 %", "status": "in_range"},
                     {"text": "Visceral fat area 118 cm² (target < 100)", "status": "out_of_range"},
                     {"text": "Bone density T-score +0.4", "status": "optimal"}],
        "radiologist": "Test Radiologist, MD", "is_test_data": True}),))

    # ---- medications, dose history, a discharge-summary document, breathing sessions
    meds = [("Vitamin D3", "2000IU", "once daily", ["08:00"], "Low vitamin D", "Dr. Meera Rao", "2026-07-10"),
            ("Magnesium glycinate", "300mg", "at night", ["22:00"], "Sleep (N-of-1)", "Self", "2026-08-25"),
            ("Omega-3", "2g", "once daily", ["13:00"], "Triglycerides", "Dr. Kavya Iyer", "2026-09-01")]
    for n, d, f, t, why, who, st in meds:
        mid = db.exec_("INSERT INTO medications (name, dose, frequency, times, reason, prescriber, start_day, active, source) "
                       "VALUES (?,?,?,?,?,?,?,1,'manual')", (n, d, f, db.j(t), why, who, st))
        for k in range(30):
            if rnd.random() < 0.85:
                day = TODAY - timedelta(days=k + 1)
                db.exec_("INSERT INTO med_doses (med_id, ts) VALUES (?,?)", (mid, f"{day.isoformat()}T{t[0]}:00"))
    db.exec_("INSERT INTO documents (kind, title, day, filename, summary, data, created_at) VALUES (?,?,?,?,?,?,?)",
             ("discharge", "Day-care discharge summary (TEST)", "2026-05-12", "discharge_test.pdf",
              "Day-care endoscopy for reflux; mild gastritis; H. pylori negative. Advised PPI for 4 weeks.",
              db.j({"meds": [{"name": "Pantoprazole", "dose": "40mg", "frequency": "once daily"}]}), now))
    for k in range(9):
        day = TODAY - timedelta(days=[0, 1, 2, 4, 6, 9, 13, 16, 20][k])
        db.exec_("INSERT INTO sessions_log (ts, kind, minutes, data) VALUES (?,?,?,?)",
                 (f"{day.isoformat()}T21:30:00", rnd.choice(["coherent", "sleep", "box"]), rnd.choice([5, 10, 10, 15]), db.j({})))

    from . import roles
    roles.seed(rnd, TODAY, sorted(sauna_days))
    from . import plans
    plans.init()
    db.exec_("INSERT INTO subscriptions (id, plan, billing, since, renews) VALUES (1,'plus','year','2026-06-01','2027-06-01')")
    engine.regenerate_insights()
    prot = db.unj(db.one("SELECT data FROM protocols WHERE active = 1")["data"])
    ids = [it["id"] for its in prot["pillars"].values() for it in its]
    for k in range(70):
        d = (TODAY - timedelta(days=k + 1)).isoformat()
        for iid in ids:
            if rnd.random() < 0.62:
                db.exec_("INSERT OR REPLACE INTO checklist (day, item_id, done) VALUES (?,?,1)", (d, iid))
    plans.generate_monthly("2026-08")
    plans.sign_monthly("2026-08", "Dr. Meera Rao", "Good month for sleep. ApoB is the priority — let's recheck in October.")
    plans.generate_monthly("2026-09")
    # A signed-off example so the thread UI has every state
    signed = db.one("SELECT id FROM insights WHERE medical = 1 ORDER BY confidence DESC")
    if signed:
        db.exec_("UPDATE insights SET review_state = 'signed' WHERE id = ?", (signed["id"],))
        db.exec_("INSERT INTO review_thread (insight_id, ts, author, action, note) VALUES (?,?,?,?,?)",
                 (signed["id"], now, "Dr. Meera Rao", "signed", "Agree. Let's discuss methylfolate at the next visit."))


if __name__ == "__main__":
    run()
    print("seeded", db.one("SELECT COUNT(*) AS n FROM signals")["n"], "signal rows,",
          db.one("SELECT COUNT(*) AS n FROM results")["n"], "lab results,",
          db.one("SELECT COUNT(*) AS n FROM insights")["n"], "insights")
