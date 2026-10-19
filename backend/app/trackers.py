"""Trackers — the person builds their own dataset by talking to Sinc.

Say anything ("my lower back hurts, about 6/10", "started magnesium 200 mg at night", "track my migraines",
"I want to quit sugar", "knee is better today, 3", "weight 92.4 kg") and Sinc:
  1. understands it  — pain (0–10 numeric rating scale, NRS), symptoms (severity 0–10), supplements, medicines,
     habits to build or break, body measurements, or any custom thing ("track <anything>");
  2. sets it up      — a tracker with a scale, a schedule and the first entry;
  3. baselines it    — the person's own median and spread from the first 7 entries (14 days for habits); until then
     the tracker says "baseline: 3 of 7";
  4. plans it        — what to log and when, which of their own signals it will be tested against, when Sinc reviews
     it, and what would end the plan (keep / drop / see a doctor);
  5. analyses it     — once ≥ 14 entries: same-day and next-day association with their sleep, HRV, resting HR, steps,
     strain and logged events (alcohol, late caffeine, hard workouts …), Spearman ρ with Benjamini–Hochberg control.
     Patterns in personal data, not causes.

Safety first: red-flag phrases (chest pain, the worst headache of one's life, one-sided weakness, fainting, blood in
vomit/stool, breathlessness at rest, thoughts of self-harm) are answered with "get care now" before anything is logged
(NHS 111 / NICE red flags; India emergency number 112, Tele-MANAS 14416). Medicines are recorded, never adjusted:
dose changes belong to the prescriber. Supplements are checked against the person's own labs (e.g. low platelets vs
blood-thinning supplements).
"""
import re
from datetime import date, datetime, timedelta

from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS trackers (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, name TEXT, kind TEXT, unit TEXT,
  scale TEXT, schedule TEXT, created_at TEXT, created_by TEXT, active INTEGER DEFAULT 1, plan TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS tracker_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, tracker_id INTEGER, ts TEXT, value REAL,
  note TEXT, source TEXT);
CREATE INDEX IF NOT EXISTS ix_tracker_entries ON tracker_entries(tracker_id, ts);
"""


_READY: set = set()


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)
    _READY.add(db.db_path())


def _ensure_schema():
    init()                                   # CREATE IF NOT EXISTS: microseconds, and safe after a DB reset


# ----------------------------------------------------------------------------- understanding

RED_FLAGS = [
    (r"chest (pain|pressure|tightness)|pain in my chest|crushing", "Chest pain or pressure can be a heart problem."),
    (r"worst headache|sudden (severe|bad) headache|thunderclap", "A sudden, severe headache needs urgent assessment."),
    (r"(one|left|right) side of my (face|body)|face (droop|drooping)|slurred speech|can'?t (move|feel) my (arm|leg)",
     "These can be signs of a stroke — every minute counts."),
    (r"faint(ed|ing)|passed out|blacked out|lost consciousness", "Fainting should be checked by a doctor."),
    (r"blood in (my )?(vomit|stool|poo|urine)|vomiting blood|black stool", "Bleeding like this needs medical care."),
    (r"can'?t breathe|short(ness)? of breath at rest|struggling to breathe", "Breathlessness at rest needs urgent care."),
    (r"kill myself|suicid|self[- ]harm|end my life|don'?t want to live", "You don't have to carry this alone."),
]
BODY = ["lower back", "upper back", "back", "neck", "shoulder", "knee", "hip", "ankle", "wrist", "elbow", "foot", "heel",
        "hamstring", "calf", "groin", "jaw", "stomach", "abdomen", "chest", "head", "joint", "joints", "muscle", "muscles",
        "leg", "arm", "hand", "eye", "eyes", "throat", "tooth", "teeth", "ear", "sciatic"]
# canonical symptom → phrases
SYMPTOMS = {
    "headache": ["headache", "head ache", "head is pounding", "sir dard", "sirdard"], "migraine": ["migraine"],
    "bloating": ["bloating", "bloated"], "acidity": ["acidity", "acid reflux", "reflux", "heartburn", "gas"],
    "constipation": ["constipation", "constipated"], "diarrhoea": ["diarrhoea", "diarrhea", "loose motion", "loose motions"],
    "nausea": ["nausea", "nauseous", "feel sick"], "fatigue": ["fatigue", "tired all", "exhausted", "no energy", "low energy"],
    "brain fog": ["brain fog", "foggy", "can't focus", "cant focus"], "anxiety": ["anxiety", "anxious", "panic"],
    "low mood": ["low mood", "feeling low", "depressed", "sad"], "insomnia": ["insomnia", "can't sleep", "cant sleep", "couldn't sleep"],
    "dizziness": ["dizzy", "dizziness", "lightheaded", "light-headed"], "palpitations": ["palpitation", "heart racing", "racing heart"],
    "cough": ["cough", "coughing"], "sore throat": ["sore throat"], "cold": ["runny nose", "blocked nose", "common cold", "a cold"],
    "fever": ["fever", "temperature"], "rash": ["rash", "hives"], "itching": ["itching", "itchy"], "cramps": ["cramp", "cramps"],
    "muscle soreness": ["sore muscles", "doms", "muscle soreness"], "stiffness": ["stiff", "stiffness"],
    "allergy": ["allergy", "sneezing", "hay fever"], "acne": ["acne", "breakout", "pimples"], "hair fall": ["hair fall", "hair loss"],
}
SUPPS = ["magnesium", "ashwagandha", "creatine", "omega-3", "omega 3", "fish oil", "vitamin d", "vitamin d3", "vitamin b12", "b12",
         "vitamin c", "zinc", "iron", "folate", "folic acid", "melatonin", "glycine", "l-theanine", "theanine", "curcumin",
         "turmeric", "whey", "protein powder", "probiotic", "collagen", "multivitamin", "electrolytes", "psyllium", "isabgol",
         "coq10", "nac", "glutathione", "berberine", "vitamin e", "ginkgo", "caffeine pills", "beetroot"]
MEDS = ["metformin", "statin", "rosuvastatin", "atorvastatin", "telmisartan", "amlodipine", "levothyroxine", "thyroxine",
        "pantoprazole", "omeprazole", "paracetamol", "ibuprofen", "aspirin", "cetirizine", "montelukast", "insulin",
        "antibiotic", "azithromycin", "amoxicillin", "sertraline", "escitalopram", "propranolol", "prednisolone"]
# What each supplement is plausibly expected to move, in the person's own data (evidence-graded elsewhere, in rx.py).
SUPP_OUTCOMES = {"magnesium": ["deep_sleep", "sleep_score"], "glycine": ["sleep_score", "deep_sleep"], "melatonin": ["sleep_hours", "sleep_score"],
                 "ashwagandha": ["hrv", "sleep_score", "rhr"], "theanine": ["sleep_score", "hrv"], "l-theanine": ["sleep_score", "hrv"],
                 "creatine": ["weight"], "omega-3": ["hrv"], "omega 3": ["hrv"], "fish oil": ["hrv"], "beetroot": ["rhr", "sbp"],
                 "electrolytes": ["hrv", "rhr"], "caffeine pills": ["sleep_score"]}
SUPP_LABS = {"vitamin d": ("vitd", 90), "vitamin d3": ("vitd", 90), "b12": ("b12", 90), "vitamin b12": ("b12", 90), "iron": ("ferritin", 90),
             "folate": ("folate", 90), "folic acid": ("folate", 90), "omega-3": ("triglycerides", 90), "fish oil": ("triglycerides", 90),
             "berberine": ("hba1c", 90), "psyllium": ("ldl", 60), "isabgol": ("ldl", 60), "zinc": ("alp", 90)}
BLOOD_THINNING = {"omega-3", "omega 3", "fish oil", "curcumin", "turmeric", "vitamin e", "ginkgo", "aspirin", "ibuprofen"}
HABIT_BREAK = r"(quit|stop|cut (out|down)( on)?|give up|reduce|less|avoid|no more)\s+(?:eating |drinking |having |taking )?(?P<h>[a-z][a-z \-]{2,30}?)(?:[.,!]|$| from| for| every| at)"
HABIT_BUILD = r"(start|begin|want to|going to|plan to|try to)\s+(?:do(?:ing)? |doing |have |having |take |taking )?(?P<h>(?:meditat|stretch|walk|journal|read|cold shower|yoga|breath|sunlight|morning light|run|lift|gym|floss|sleep by|bed by|wake up|no phone)[a-z \-:0-9]{0,30}?)(?:[.,!]|$| every| daily| each)"
MEASURE = [
    (r"\bweigh(?:t|ed|ing)?\b[^0-9]{0,12}(\d{2,3}(?:\.\d)?)\s*(kg|kgs|kilos)?", "weight", "kg"),
    (r"\b(?:bp|blood pressure)\b[^0-9]{0,12}(\d{2,3})\s*/\s*(\d{2,3})", "bp", "mmHg"),
    (r"\b(?:sugar|glucose)\b[^0-9]{0,15}(\d{2,3})\b", "glucose_spot", "mg/dL"),
    (r"\bwaist\b[^0-9]{0,12}(\d{2,3}(?:\.\d)?)\s*(cm|in|inch|inches)?", "waist", "cm"),
]


def _sev(t: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d)?)\s*(?:/|out of)\s*10\b", t) or re.search(r"\b(?:pain|severity|level|at|about|around|is)\s+(?:a\s+)?(\d+(?:\.\d)?)\b(?!\s*(?:am|pm|kg|mg|min|hours?|days?))", t)
    if m and 0 <= float(m.group(1)) <= 10:
        return float(m.group(1))
    m = re.search(r"[,:\-]\s*(\d+(?:\.\d)?)\s*$", t.strip()) or re.search(r"^\s*(\d+(?:\.\d)?)\s*$", t)
    if m and 0 <= float(m.group(1)) <= 10:
        return float(m.group(1))
    for w, v in (("unbearable", 9), ("excruciating", 9), ("severe", 8), ("really bad", 7), ("very bad", 7), ("bad", 6),
                 ("moderate", 5), ("mild", 3), ("a bit", 2), ("slight", 2), ("little", 2), ("better", None), ("gone", 0),
                 ("no pain", 0), ("fine now", 0)):
        if re.search(rf"\b{w}\b", t):
            return v
    return None


def _when(t: str) -> str:
    now = datetime.fromisoformat(engine.now_iso())
    if "yesterday" in t or "last night" in t:
        now -= timedelta(days=1)
    return now.isoformat(timespec="minutes")


def _dose(t: str, name: str) -> str | None:
    m = re.search(rf"{re.escape(name)}[^0-9]{{0,20}}(\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|iu|ml|tablets?|capsules?|scoops?))", t) or \
        re.search(rf"(\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|iu|ml))\s+(?:of\s+)?{re.escape(name)}", t)
    return m.group(1) if m else None


def _timing(t: str) -> str | None:
    for w in ("before bed", "at night", "night", "morning", "with breakfast", "with lunch", "with dinner", "after workout", "empty stomach"):
        if w in t:
            return w
    return None


def understand(text: str) -> dict:
    """Any statement → red flag, or a list of things to track (each becomes a tracker + an entry)."""
    t = " " + re.sub(r"\s+", " ", text.lower().replace("’", "'")) + " "
    for pat, why in RED_FLAGS:
        if re.search(pat, t):
            return {"red_flag": why, "items": []}
    items, ts = [], _when(t)
    # explicit: "track X" / "start tracking X" / "log my X"
    m = re.search(r"\b(?:track|tracking|monitor|log)\s+(?:my\s+|how\s+)?(?P<x>[a-z][a-z0-9 \-']{2,40}?)(?:[.,!?]|$| every| daily| each| for| and)", t)
    explicit = re.sub(r"^((how\s+)?(often|much|many|bad)\s+(do\s+)?(i\s+|my\s+)?|my\s+|the\s+|when\s+i\s+)", "", m.group("x").strip()) if m else None
    # pain: "<body part> pain", "pain in my <part>", "my <part> hurts/aches/is sore"
    for part in sorted(BODY, key=len, reverse=True):
        if re.search(rf"\b{part}\s+(pain|ache|aches|hurts|hurting|is sore|is killing|is stiff)|pain in (my|the) {part}\b|\bmy {part}\s+(is\s+)?(hurts?|aching|sore|killing|stiff|painful|better|worse)", t):
            if part in ("head",):
                break
            items.append({"kind": "pain", "key": f"pain_{part.replace(' ', '_')}", "name": f"{part.capitalize()} pain", "value": _sev(t), "ts": ts})
            break
    for canon, phrases in SYMPTOMS.items():
        if any(re.search(rf"\b{re.escape(p)}(s|es)?\b", t) for p in phrases):
            items.append({"kind": "symptom", "key": f"sym_{canon.replace(' ', '_')}", "name": canon.capitalize(), "value": _sev(t), "ts": ts})
    took = re.search(r"\b(took|taking|take|started|start|starting|on|begun|began|having|had|stopped|stop)\b", t)
    for s in sorted(SUPPS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(s)}\b", t) and took and not any(s in i["name"].lower() for i in items):
            stop = bool(re.search(rf"\b(stopped|stop|quit)\b[^.]*{re.escape(s)}", t))
            items.append({"kind": "supplement", "key": f"supp_{re.sub(r'[^a-z0-9]+', '_', s)}", "name": s.title() if len(s) > 3 else s.upper(),
                          "value": 0.0 if stop else 1.0, "dose": _dose(t, s), "timing": _timing(t), "stopped": stop, "ts": ts, "raw": s})
            break
    for md in MEDS:
        if re.search(rf"\b{md}\b", t):
            items.append({"kind": "medicine", "key": f"med_{md}", "name": md.title(), "value": 1.0, "dose": _dose(t, md), "timing": _timing(t), "ts": ts})
            break
    for pat, key, unit in MEASURE:
        mm = re.search(pat, t)
        if mm:
            if key == "bp":
                items.append({"kind": "measure", "key": "bp", "name": "Blood pressure", "value": float(mm.group(1)), "value2": float(mm.group(2)), "unit": unit, "ts": ts})
            else:
                v = float(mm.group(1))
                if key == "waist" and (mm.group(2) or "").startswith("in"):
                    v = round(v * 2.54, 1)
                items.append({"kind": "measure", "key": key, "name": key.replace("_", " ").capitalize().replace("spot", "(finger-prick)"), "value": v, "unit": unit, "ts": ts})
    hb = re.search(HABIT_BREAK, t)
    if hb and not any(i["kind"] in ("supplement", "medicine") for i in items):
        h = re.sub(r"^(the|my)\s+", "", hb.group("h").strip())
        items.append({"kind": "habit_break", "key": "habit_" + re.sub(r"[^a-z0-9]+", "_", h), "name": f"Less {h}", "value": None, "ts": ts, "habit": h})
    hm = re.search(HABIT_BUILD, t)
    if hm:
        h = hm.group("h").strip()
        items.append({"kind": "habit_build", "key": "habit_" + re.sub(r"[^a-z0-9]+", "_", h), "name": h.capitalize(), "value": None, "ts": ts, "habit": h})
    if explicit and not any(explicit in i["name"].lower() or i["name"].lower().split()[0] in explicit for i in items):
        known = next((i for i in understand(explicit)["items"]), None) if explicit != text.lower().strip() else None
        if known:
            known["value"] = None
            items.append(known)
        else:
            items.append({"kind": "custom", "key": "custom_" + re.sub(r"[^a-z0-9]+", "_", explicit)[:40], "name": explicit.capitalize(),
                          "value": _sev(t), "ts": ts})
    seen, out = set(), []
    for i in items:
        if i["key"] not in seen:
            seen.add(i["key"]); out.append(i)
    return {"red_flag": None, "items": out, "explicit": bool(explicit)}


# ----------------------------------------------------------------------------- setup, baseline, plan

SCALES = {"pain": ("0–10", "0–10 scale (0 = no pain, 10 = worst imaginable; the clinical numeric rating scale)"),
          "symptom": ("0–10", "0–10 scale (0 = none, 10 = as bad as it gets)"),
          "supplement": ("taken", "1 = taken that day, 0 = not taken"), "medicine": ("taken", "1 = taken as prescribed, 0 = missed"),
          "habit_break": ("count", "how many times that day (0 is the goal)"), "habit_build": ("done", "1 = done that day"),
          "measure": ("value", "the reading"), "custom": ("0–10", "a 0–10 score or a count — whatever fits")}


def _labv(marker):
    return db.one("""SELECT r.value_num AS v, r.ref_low AS lo, rp.collected_on AS d FROM results r JOIN reports rp ON rp.id = r.report_id
                     WHERE r.marker_id = ? AND r.value_num IS NOT NULL ORDER BY rp.is_test_data ASC, rp.collected_on DESC LIMIT 1""", (marker,))


def _plan(it: dict) -> dict:
    k = it["kind"]
    today = date.fromisoformat(engine.now_iso()[:10])
    review = (today + timedelta(days=14)).isoformat()
    tests = ["sleep", "HRV", "resting heart rate", "steps", "daily strain", "alcohol", "late caffeine", "hard workouts", "late meals"]
    warn = []
    if k in ("pain", "symptom"):
        steps = [f"Rate it once a day, ideally at the same time (evening), on the {SCALES[k][1]}.",
                 "Tell me what you think set it off when it flares — food, posture, a workout, stress — in your own words.",
                 f"After 14 ratings I test it against your {', '.join(tests[:5])} and logged {', '.join(tests[5:])} (same day and next day)."]
        stop = "See a doctor sooner if it's ≥ 7/10, wakes you at night, keeps getting worse for a week, or comes with fever, numbness or weight loss."
        watch = ["sleep_score", "hrv", "rhr", "steps"]
    elif k == "supplement":
        s = it.get("raw", it["name"].lower())
        outs, lab = SUPP_OUTCOMES.get(s, []), SUPP_LABS.get(s)
        steps = [f"Log it each day you take it{f' ({it['dose']})' if it.get('dose') else ''}{f', {it['timing']}' if it.get('timing') else ''} — or just tell me \"took {s}\"."]
        if outs:
            labels = ", ".join(engine.SIGNALS[o][0].lower() for o in outs if o in engine.SIGNALS)
            steps.append(f"Your 14 days before it are the baseline; after 28 days on it I compare your {labels} on vs off.")
            steps.append("For a cleaner answer, run it as an N-of-1 study (2 weeks on, 2 weeks off, twice) from the Studies screen.")
        if lab:
            steps.append(f"Its real target is a blood marker ({lab[0]}); retest in about {lab[1]} days to see if it moved.")
            review = (today + timedelta(days=lab[1])).isoformat()
        if not outs and not lab:
            steps.append("I don't have a validated signal for this one; tell me how you feel on it (0–10) and I'll track that.")
        stop = "Supplements are not a substitute for prescribed medicine; check with your doctor if you take any."
        plt = _labv("platelets")
        if s in BLOOD_THINNING and plt and plt["lo"] and plt["v"] < plt["lo"]:
            warn.append(f"Your platelets were {plt['v']:g} on {plt['d']} (below range). {it['name']} can thin the blood — please ask your doctor before taking it.")
        watch = outs
    elif k == "medicine":
        steps = ["Tell me each dose (\"took metformin\") or I'll ask once a day.",
                 "I'll watch your signals around it and flag anything unusual for your doctor."]
        stop = "I never change medicine doses — only your prescriber does. Don't stop a prescribed medicine without asking them."
        watch = ["rhr", "hrv", "sleep_score", "glucose_mean"]
    elif k == "habit_break":
        steps = [f"Tell me each time it happens (\"had {it.get('habit', 'it')}\"), or a daily count. Zero days count too — say \"no {it.get('habit', 'it')} today\".",
                 "Your first 14 days are the baseline; the goal is to bring the weekly count down, not to be perfect.",
                 "Each week I show your streak and whether your sleep, HRV and resting heart rate moved with it."]
        stop = "If you slip, keep logging — honest data beats a perfect streak."
        watch = ["sleep_score", "hrv", "rhr"]
    elif k == "habit_build":
        steps = [f"Tell me when you've done it (\"done {it.get('habit', 'it')}\").", "Baseline is your first 14 days; then I show your weekly rate and what it changes."]
        stop = "Start small: a habit you keep beats a big one you drop."
        watch = ["sleep_score", "hrv", "rhr", "steps"]
    elif k == "measure":
        steps = ["Measure at the same time of day, same conditions (for weight: morning, after the toilet, before food)."]
        if it["key"] == "bp":
            steps.append("For blood pressure: sit 5 minutes, arm at heart level, take two readings a minute apart (ESC/ESH 2023).")
        stop = "A home reading is not a diagnosis; bring the trend to your doctor."
        watch = []
    else:
        steps = [f"Tell me about it whenever it happens, with a number if you can ({SCALES['custom'][1]}).",
                 f"After 14 entries I look for what moves it in your {', '.join(tests[:5])}."]
        stop = "Tell me more about it any time and I'll refine the tracker."
        watch = ["sleep_score", "hrv", "rhr", "steps"]
    return {"steps": steps, "review_on": review, "watch": watch, "safety": stop, "warnings": warn,
            "baseline_needed": 14 if k.startswith("habit") or k in ("supplement", "medicine") else 7}


def _ensure(it: dict, by: str) -> tuple[dict, bool]:
    r = db.one("SELECT * FROM trackers WHERE key = ?", (it["key"],))
    if r:
        if not r["active"]:
            db.exec_("UPDATE trackers SET active = 1 WHERE id = ?", (r["id"],))
        return r, False
    plan = _plan(it)
    scale = SCALES[it["kind"]]
    tid = db.exec_("""INSERT INTO trackers (key, name, kind, unit, scale, schedule, created_at, created_by, plan, data)
                      VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (it["key"], it["name"], it["kind"], it.get("unit") or "", scale[0],
                    "daily" if it["kind"] in ("pain", "symptom", "supplement", "medicine", "habit_build") else "when it happens",
                    engine.now_iso(), by, db.j(plan), db.j({k: it.get(k) for k in ("dose", "timing", "raw", "habit") if it.get(k)})))
    if it["kind"] == "medicine":
        db.exec_("INSERT INTO medications (name, dose, frequency, times, reason, prescriber, start_day, active, source) VALUES (?,?,?,?,?,?,?,?,?)",
                 (it["name"], it.get("dose"), None, it.get("timing"), None, None, it["ts"][:10], 1, "told Sinc"))
    return db.one("SELECT * FROM trackers WHERE id = ?", (tid,)), True


def log_entry(tid: int, value: float | None, ts: str | None = None, note: str | None = None, source: str = "sinc") -> int:
    return db.exec_("INSERT INTO tracker_entries (tracker_id, ts, value, note, source) VALUES (?,?,?,?,?)",
                    (tid, ts or engine.now_iso(), value, (note or "")[:300], source))


def baseline(tid: int) -> dict:
    tr = db.one("SELECT * FROM trackers WHERE id = ?", (tid,))
    if tr["kind"] in ("supplement", "medicine"):
        # the baseline for something you take is YOU before it: the watched signals over the 14 days before you started
        start = tr["created_at"][:10]
        b4 = (date.fromisoformat(start) - timedelta(days=14)).isoformat()
        bits = []
        for m in db.unj(tr["plan"], {}).get("watch", []):
            v = [x for _, x in engine.series(m, b4, (date.fromisoformat(start) - timedelta(days=1)).isoformat())]
            if len(v) >= 5 and m in engine.SIGNALS:
                lab, unit, _, dec = engine.SIGNALS[m]
                bits.append(f"{lab.lower()} {round(sum(v) / len(v), dec or None)} {unit}".strip())
        return {"ready": bool(bits), "text": ("Baseline before you started (14 days): " + ", ".join(bits)) if bits else
                "Baseline: I don't have 14 days of your signals before you started, so I'll compare on and off weeks instead"}
    need = db.unj(tr["plan"], {}).get("baseline_needed", 7)
    rows = db.rows("SELECT ts, value FROM tracker_entries WHERE tracker_id = ? AND value IS NOT NULL ORDER BY ts", (tid,))
    days = _daily(rows, tr["kind"])
    if len(days) < need:
        return {"ready": False, "have": len(days), "need": need, "text": f"Baseline: {len(days)} of {need} days"}
    first = sorted(v for _, v in days[:need])
    med = first[len(first) // 2]
    q1, q3 = first[len(first) // 4], first[(3 * len(first)) // 4]
    recent = [v for _, v in days[-7:]]
    now = sum(recent) / len(recent)
    return {"ready": True, "median": round(med, 2), "iqr": [round(q1, 2), round(q3, 2)], "last7_mean": round(now, 2),
            "change": round(now - med, 2), "days": len(days),
            "text": f"Your baseline is {med:g} (usual range {q1:g}–{q3:g}); the last 7 days average {now:.1f}."}


def _daily(rows, kind) -> list[tuple[str, float]]:
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault(r["ts"][:10], []).append(float(r["value"]))
    agg = (lambda v: sum(v)) if kind in ("habit_break",) else (lambda v: max(v)) if kind in ("pain", "symptom") else (lambda v: v[-1])
    return sorted((d, agg(v)) for d, v in by.items())


# ----------------------------------------------------------------------------- analysis

def _rank(x):
    o = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def _spearman(a, b):
    import math
    n = len(a)
    ra, rb = _rank(a), _rank(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) or 1e-9
    rho = num / den
    t = rho * math.sqrt(max(n - 2, 1) / max(1e-9, 1 - rho ** 2))
    p = 2 * (1 - engine._phi(abs(t)))
    return rho, p


def drivers(tid: int, min_days: int = 14) -> dict:
    """What moves with this tracker: signals the same day and the day before, logged events the day before."""
    tr = db.one("SELECT * FROM trackers WHERE id = ?", (tid,))
    days = dict(_daily(db.rows("SELECT ts, value FROM tracker_entries WHERE tracker_id = ? AND value IS NOT NULL", (tid,)), tr["kind"]))
    if len(days) < min_days:
        return {"ready": False, "have": len(days), "need": min_days, "text": f"I need {min_days - len(days)} more days of entries before I look for patterns."}
    tests = []
    for m in ("sleep_hours", "sleep_score", "deep_sleep", "hrv", "rhr", "steps", "exercise_min", "skin_temp"):
        s = dict(engine.series(m))
        for lag, lbl in ((0, "same day"), (1, "the day before")):
            pairs = [(v, s[(date.fromisoformat(d) - timedelta(days=lag)).isoformat()]) for d, v in days.items()
                     if (date.fromisoformat(d) - timedelta(days=lag)).isoformat() in s]
            if len(pairs) >= min_days:
                rho, p = _spearman([a for a, _ in pairs], [b for _, b in pairs])
                tests.append({"driver": f"{engine.SIGNALS[m][0]} ({lbl})", "rho": round(rho, 2), "p": p, "n": len(pairs)})
    ev: dict[str, set] = {}
    for e in db.rows("SELECT ts, kind FROM events"):
        ev.setdefault(e["kind"], set()).add(e["ts"][:10])
    for kind, ds in ev.items():
        if len(ds) < 4 or kind in ("note", "meal", "mood"):
            continue
        xs = [(v, 1.0 if (date.fromisoformat(d) - timedelta(days=1)).isoformat() in ds else 0.0) for d, v in days.items()]
        if 3 <= sum(b for _, b in xs) <= len(xs) - 3:
            rho, p = _spearman([a for a, _ in xs], [b for _, b in xs])
            tests.append({"driver": f"{engine.EVENT_KINDS.get(kind, kind)} (the day before)", "rho": round(rho, 2), "p": p, "n": len(xs)})
    cut = engine.bh_threshold([t["p"] for t in tests]) if tests else 0
    found = sorted([t for t in tests if t["p"] <= cut and abs(t["rho"]) >= 0.3], key=lambda t: -abs(t["rho"]))
    for t in found:
        t["text"] = (f"Higher {tr['name'].lower()} goes with {'higher' if t['rho'] > 0 else 'lower'} {t['driver'][0].lower() + t['driver'][1:]} "
                     f"(ρ {t['rho']:+.2f}, {t['n']} days, {engine.fmt_p(t['p'])})")
    return {"ready": True, "tests": len(tests), "found": found[:6],
            "text": ("; ".join(t["text"] for t in found[:3]) + ". Patterns in your data, not proof of cause.") if found else
                    f"Across {len(tests)} comparisons nothing stands out yet (Benjamini–Hochberg controlled). That is a real answer too.",
            "method": "Spearman rank correlation, same-day and 1-day lag, Benjamini–Hochberg q = 0.05, |ρ| ≥ 0.3"}


# ----------------------------------------------------------------------------- the conversation entry point

def capture(text: str, by: str = "sinc") -> dict | None:
    """Called on every message to Sinc. Returns None for pure questions or when nothing trackable was said."""
    _ensure_schema()
    bare = re.fullmatch(r"\s*(\d+(?:\.\d)?)\s*(?:/\s*10|out of 10)?\s*\.?\s*", text)
    if bare and 0 <= float(bare.group(1)) <= 10:
        since = (datetime.fromisoformat(engine.now_iso()) - timedelta(minutes=30)).isoformat(timespec="minutes")
        w = db.one("SELECT * FROM trackers WHERE json_extract(data, '$.awaiting') >= ? ORDER BY json_extract(data, '$.awaiting') DESC", (since,))
        if w:
            v = float(bare.group(1))
            log_entry(w["id"], v, note=text, source=by)
            d = db.unj(w["data"], {}); d.pop("awaiting", None)
            db.exec_("UPDATE trackers SET data = ? WHERE id = ?", (db.j(d), w["id"]))
            t = {**summary(w["id"]), "new": False, "logged": v, "stopped": False}
            return {"red_flag": False, "trackers": [t], "answer": _reply([t]), "medical": False}
    hit = _habit_log(text, by)
    if hit:
        return hit
    u = understand(text)
    if u["red_flag"]:
        crisis = "self" in u["red_flag"] or "alone" in u["red_flag"]
        msg = (f"{u['red_flag']} Please don't wait on an app for this — " +
               ("call Tele-MANAS on 14416 (free, 24×7, India) or 112 if you are in danger, and tell someone you trust now."
                if crisis else "call 112 or get to an emergency department now. If it has already passed, see a doctor today."))
        return {"red_flag": True, "answer": msg, "trackers": [], "medical": True}
    if not u["items"]:
        return None
    if text.strip().endswith("?") and not u.get("explicit"):
        return None
    out = []
    for it in u["items"]:
        tr, new = _ensure(it, by)
        if it.get("value") is not None or it["kind"] in ("supplement", "medicine", "measure"):
            v = it.get("value")
            if v is not None:
                log_entry(tr["id"], v, it["ts"], text, by)
            if it["kind"] == "measure":
                if it["key"] == "weight":
                    db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (it["ts"][:10], "weight", v, "told Sinc"))
                if it["key"] == "bp":
                    for mtr, val in (("sbp", it["value"]), ("dbp", it["value2"])):
                        db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (it["ts"][:10], mtr, val, "told Sinc"))
            if it["kind"] in ("supplement", "medicine") and not it.get("stopped"):
                db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)",
                         (it["ts"], "supplement" if it["kind"] == "supplement" else "medication", it["name"], None, db.j({"via": "sinc", "dose": it.get("dose")})))
            if it.get("stopped"):
                db.exec_("UPDATE trackers SET active = 0 WHERE id = ?", (tr["id"],))
        elif it["kind"] in ("pain", "symptom", "custom"):
            d = db.unj(tr["data"], {}); d["awaiting"] = engine.now_iso()
            db.exec_("UPDATE trackers SET data = ? WHERE id = ?", (db.j(d), tr["id"]))
        if it["kind"] in ("pain", "symptom") and it.get("value") is None:
            db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (it["ts"], "symptom", it["name"], None, db.j({"via": "sinc"})))
        out.append({**summary(tr["id"]), "new": new, "logged": it.get("value"), "stopped": it.get("stopped", False)})
    return {"red_flag": False, "trackers": out, "answer": _reply(out), "medical": any(t["kind"] == "medicine" for t in out)}


def _habit_log(text: str, by: str) -> dict | None:
    """'had sugar' / 'no sugar today' / '2 cigarettes' / 'meditated' against an existing habit tracker."""
    t = text.lower()
    for tr in db.rows("SELECT * FROM trackers WHERE active = 1 AND kind IN ('habit_break', 'habit_build')"):
        h = db.unj(tr["data"], {}).get("habit") or tr["name"].lower()
        stem = h.split()[0][:max(4, len(h.split()[0]) - 3)]
        if not re.search(rf"\b{re.escape(stem)}", t) or re.search(r"\b(quit|stop|want to|start|begin|track)\b", t):
            continue
        if re.search(r"\b(no|none|zero|didn'?t|did not|skipped|avoided|without)\b", t):
            v = 0.0 if tr["kind"] == "habit_break" else 0.0
        else:
            m = re.search(r"\b(\d+)\b", t)
            v = float(m.group(1)) if m and tr["kind"] == "habit_break" else 1.0
        log_entry(tr["id"], v, note=text, source=by)
        x = {**summary(tr["id"]), "new": False, "logged": v, "stopped": False}
        return {"red_flag": False, "trackers": [x], "answer": _reply([x]), "medical": False}
    return None


def summary(tid: int) -> dict:
    tr = db.one("SELECT * FROM trackers WHERE id = ?", (tid,))
    n = db.one("SELECT COUNT(*) AS n FROM tracker_entries WHERE tracker_id = ?", (tid,))["n"]
    return {"id": tr["id"], "key": tr["key"], "name": tr["name"], "kind": tr["kind"], "scale": tr["scale"], "schedule": tr["schedule"],
            "active": bool(tr["active"]), "entries": n, "plan": db.unj(tr["plan"], {}), "baseline": baseline(tid), "data": db.unj(tr["data"], {})}


def _reply(ts: list[dict]) -> str:
    parts = []
    for t in ts:
        p = t["plan"]
        if t["stopped"]:
            parts.append(f"Noted that you stopped **{t['name']}**. I've paused its tracker; your data so far stays, and I'll compare before and after.")
            continue
        logged = f" — logged {t['logged']:g}{'/10' if t['scale'] == '0–10' else ''}" if t["logged"] is not None and t["kind"] not in ("supplement", "medicine") else ""
        if t["new"]:
            parts.append(f"I've set up a tracker for **{t['name']}**{logged}.")
            parts += [f"- {s}" for s in p.get("steps", [])]
            parts.append(f"- {t['baseline']['text']}. I'll review it with you on {p.get('review_on')}.")
            if p.get("safety"):
                parts.append(f"_{p['safety']}_")
        else:
            parts.append(f"**{t['name']}**{logged or ' — noted'}. {t['baseline']['text']}.")
        parts += [f"**Please note:** {w}" for w in p.get("warnings", [])]
        if t["kind"] in ("pain", "symptom", "custom") and t["logged"] is None:
            parts.append(f"How bad is the {t['name'].lower()} right now, 0–10? Just reply with the number.")
        if t["kind"] in ("pain", "symptom") and t["logged"] is not None and t["logged"] >= 7:
            parts.append("That's a high score. If it stays this bad or is new and unexplained, please see a doctor soon.")
    return "\n".join(parts)


def today() -> list[dict]:
    """Daily trackers still waiting for today's entry — the evening check-in."""
    d = engine.now_iso()[:10]
    out = []
    for tr in db.rows("SELECT * FROM trackers WHERE active = 1 AND schedule = 'daily'"):
        done = db.one("SELECT 1 AS x FROM tracker_entries WHERE tracker_id = ? AND substr(ts,1,10) = ?", (tr["id"], d))
        if not done:
            out.append({"id": tr["id"], "name": tr["name"], "kind": tr["kind"], "scale": tr["scale"],
                        "ask": f"How is your {tr['name'].lower()} today (0–10)?" if tr["scale"] == "0–10" else f"Did you take {tr['name']} today?"
                        if tr["kind"] in ("supplement", "medicine") else f"Did you do {tr['name'].lower()} today?"})
    return out


def all_trackers(active_only: bool = False) -> list[dict]:
    q = "SELECT id FROM trackers" + (" WHERE active = 1" if active_only else "") + " ORDER BY created_at DESC"
    return [summary(r["id"]) for r in db.rows(q)]
