"""Iteration-3 features: activity dashboard, categories, medications, notifications, clinician notes,
meditation stats, document intake (prescriptions / discharge summaries)."""
import re
from datetime import date, datetime, timedelta

from . import db, derived, engine
from .catalog import MARKERS
from .catalog_ext import CONCERNS

# ------------------------------------------------------------------ activity dashboard (rings, gauges, vitals)

def _val(metric, day):
    r = db.one("SELECT value, source FROM signals WHERE metric = ? AND day = ?", (metric, day))
    return (r["value"], r["source"]) if r else (None, None)


def dashboard(day: str) -> dict:
    goals = {"steps": 10000, "exercise_min": 30, "active_kcal": 500, **(engine.profile().get("goals") or {})}
    rings = []
    for m, label in (("active_kcal", "Move"), ("exercise_min", "Exercise"), ("steps", "Steps")):
        v, src = _val(m, day)
        rings.append({"id": m, "label": label, "value": v, "goal": goals.get(m), "pct": round(100 * v / goals[m]) if v else 0,
                      "unit": engine.SIGNALS[m][1], "source": src})
    # Recovery: HRV + RHR vs 30-day baseline. Strain: exercise + steps load. Sleep: score.
    hrv, _ = _val("hrv", day)
    rhr, _ = _val("rhr", day)
    bh = engine.signal_baseline("hrv", day, 30)
    br = engine.signal_baseline("rhr", day, 30)
    recovery = None
    if hrv and rhr and bh and br and bh["sd"] and br["sd"]:
        z = (hrv - bh["mean"]) / bh["sd"] - (rhr - br["mean"]) / br["sd"]
        recovery = max(0, min(100, round(50 + 18 * z)))
    ex, _ = _val("exercise_min", day)
    st, _ = _val("steps", day)
    strain = round(min(21, (ex or 0) / 6 + (st or 0) / 2500), 1) if ex is not None else None
    sleep, _ = _val("sleep_score", day)
    # Stress proxy (HRV below baseline) — labelled as an estimate.
    stress = None if not (hrv and bh and bh["sd"]) else max(0, min(100, round(50 - 20 * (hrv - bh["mean"]) / bh["sd"])))
    vitals = []
    for m in ("rhr", "hrv", "spo2", "resp_rate", "skin_temp", "sleep_hours", "deep_sleep", "glucose_mean"):
        v, src = _val(m, day)
        b = engine.signal_baseline(m, day, 30)
        vitals.append({"id": m, "label": engine.SIGNALS[m][0], "unit": engine.SIGNALS[m][1], "value": v, "source": src,
                       "baseline": b["mean"] if b else None, "sd": b["sd"] if b else None,
                       "flag": None if v is None or not b or not b["sd"] else
                       ("high" if v > b["mean"] + 2 * b["sd"] else "low" if v < b["mean"] - 2 * b["sd"] else "normal")})
    # Activity heatmap for the last 9 weeks (exercise minutes per day)
    end = date.fromisoformat(day)
    heat = []
    for i in range(62, -1, -1):
        d = (end - timedelta(days=i)).isoformat()
        v, _ = _val("exercise_min", d)
        heat.append({"day": d, "value": v})
    return {"day": day, "rings": rings, "recovery": recovery, "strain": strain, "sleep_score": sleep, "stress": stress,
            "stress_note": "Estimated from HRV versus your 30-day baseline", "vitals": vitals, "heatmap": heat,
            "methods": {"recovery": "50 + 18 × (HRV z-score − RHR z-score) vs 30-day baseline, clamped 0–100",
                        "strain": "exercise min ÷ 6 + steps ÷ 2,500, capped at 21"}}

# ------------------------------------------------------------------ browse by category (Apple Health style)

CATEGORIES = {
    "Activity": {"signals": ["steps", "active_kcal", "exercise_min", "vo2max"], "concern": "Fitness & cardiorespiratory"},
    "Body measurements": {"signals": ["weight"], "concern": "Muscle, bone & mobility"},
    "Heart": {"signals": ["rhr", "hrv"], "concern": "Heart & arteries"},
    "Sleep": {"signals": ["sleep_hours", "deep_sleep", "rem_sleep", "sleep_score"], "concern": "Sleep"},
    "Respiratory & vitals": {"signals": ["spo2", "resp_rate", "skin_temp"], "concern": None},
    "Metabolic": {"signals": ["glucose_mean"], "concern": "Blood sugar & metabolism"},
    "Mental wellbeing": {"signals": ["mindful_min", "daylight_min"], "concern": None},
    "Liver & kidney": {"signals": [], "concern": "Liver"},
    "Brain": {"signals": [], "concern": "Brain & cognition"},
    "Hormones": {"signals": [], "concern": "Hormones & thyroid"},
    "Inflammation & immunity": {"signals": [], "concern": "Inflammation & immunity"},
    "Gut": {"signals": [], "concern": "Gut"},
    "Nutrients": {"signals": [], "concern": "Nutrients"},
    "Toxins": {"signals": [], "concern": "Toxins & detox"},
    "Cancer screening": {"signals": [], "concern": "Cancer screening"},
}


def categories() -> list[dict]:
    L = engine.latest_values()
    out = []
    for name, spec in CATEGORIES.items():
        sigs = [s for s in spec["signals"] if engine.series(s)]
        markers = [m for m in CONCERNS.get(spec["concern"] or "", []) if m in L]
        flagged = sum(1 for m in markers if L[m]["status"] in ("out_of_range", "variant", "detected"))
        out.append({"name": name, "signals": len(sigs), "markers": len(markers), "flagged": flagged,
                    "empty": not sigs and not markers})
    return out


def category(name: str) -> dict:
    spec = CATEGORIES[name]
    L = engine.latest_values()
    sigs = []
    for s in spec["signals"]:
        ser = engine.series(s)
        if ser:
            lab, unit, _, dec = engine.SIGNALS[s]
            sigs.append({"id": s, "label": lab, "unit": unit, "value": round(ser[-1][1], dec or 1), "day": ser[-1][0],
                         "spark": [v for _, v in ser[-7:]]})
    missing_sigs = [engine.SIGNALS[s][0] for s in spec["signals"] if not engine.series(s)]
    ms = CONCERNS.get(spec["concern"] or "", [])
    markers = [{"id": m, "name": MARKERS[m][0], "value": L[m]["value_num"] if L[m]["value_num"] is not None else L[m]["value_text"],
                "unit": L[m]["unit"], "status": L[m]["status"], "day": L[m]["collected_on"]} for m in ms if m in L]
    not_tested = [MARKERS[m][0] for m in ms if m not in L and m in MARKERS]
    return {"name": name, "signals": sigs, "markers": markers, "no_data": missing_sigs + not_tested}

# ------------------------------------------------------------------ pinned cards

DEFAULT_PINS = ["rhr", "steps", "deep_sleep"]


def pins() -> list[str]:
    return engine.profile().get("pins") or DEFAULT_PINS

# ------------------------------------------------------------------ medications

INTERACTIONS = [
    ({"statin", "atorvastatin", "rosuvastatin", "simvastatin"}, {"grapefruit", "clarithromycin", "niacin"},
     "Statins with grapefruit or clarithromycin raise statin levels and myopathy risk."),
    ({"warfarin"}, {"aspirin", "ibuprofen", "omega-3", "fish oil", "vitamin k"}, "Bleeding risk changes with warfarin."),
    ({"metformin"}, {"alcohol"}, "Alcohol with metformin increases lactic-acidosis risk."),
    ({"levothyroxine"}, {"calcium", "iron", "magnesium", "coffee"}, "Take levothyroxine 4 hours apart from calcium, iron or magnesium."),
    ({"ssri", "sertraline", "fluoxetine", "escitalopram"}, {"st john", "tramadol", "5-htp"}, "Serotonin syndrome risk."),
    ({"potassium"}, {"ace inhibitor", "lisinopril", "spironolactone", "telmisartan"}, "High potassium risk."),
    ({"magnesium"}, {"antibiotic", "doxycycline", "ciprofloxacin"}, "Magnesium reduces absorption of some antibiotics — separate by 2–4 h."),
]


def meds(today: str | None = None) -> list[dict]:
    rows = db.rows("SELECT * FROM medications ORDER BY active DESC, name")
    today = today or engine.last_signal_day() or date.today().isoformat()
    for r in rows:
        r["times"] = db.unj(r["times"], [])
        taken = db.rows("SELECT ts FROM med_doses WHERE med_id = ? AND substr(ts,1,10) = ?", (r["id"], today))
        r["taken_today"] = len(taken)
        last30 = db.one("SELECT COUNT(*) AS n FROM med_doses WHERE med_id = ? AND ts >= ? AND ts < ?",
                        (r["id"], (date.fromisoformat(today) - timedelta(days=30)).isoformat(), today))["n"]
        expected = 30 * max(len(r["times"]), 1)
        r["adherence_30d"] = round(100 * min(last30, expected) / expected)
    return rows


def interactions() -> list[dict]:
    names = [m["name"].lower() for m in db.rows("SELECT name FROM medications WHERE active = 1")]
    if db.one("SELECT 1 AS x FROM events WHERE kind = 'alcohol' AND ts >= date('now', '-30 day')"):
        names.append("alcohol")
    hits = []
    for a, b, msg in INTERACTIONS:
        ia = [n for n in names if any(x in n for x in a)]
        ib = [n for n in names if any(x in n for x in b)]
        if ia and ib:
            hits.append({"between": [ia[0], ib[0]], "message": msg, "severity": "check with your clinician"})
    return hits

# ------------------------------------------------------------------ notifications

def notifications(today: str) -> list[dict]:
    out = []
    for n in derived.retest_nudges(today):
        out.append({"kind": "retest", "title": f"Retest due: {', '.join(m['name'] for m in n['markers'][:3])}",
                    "body": n["text"], "route": "/(tabs)/vault", "ts": today})
    for t in db.rows("""SELECT t.*, i.title FROM review_thread t JOIN insights i ON i.id = t.insight_id
                        WHERE t.author NOT IN ('You', 'Sinc') ORDER BY t.ts DESC LIMIT 10"""):
        out.append({"kind": "review", "title": f"{t['author']} {t['action']} a Sinc draft", "body": t["title"],
                    "route": f"/insight/{t['insight_id']}", "ts": t["ts"]})
    for i in engine.list_insights()[:5]:
        if i["kind"] == "cross_panel" and i["confidence"] >= 0.75:
            out.append({"kind": "insight", "title": "New pattern across your reports", "body": i["title"],
                        "route": f"/insight/{i['id']}", "ts": i["created_at"]})
    for a in db.rows("SELECT a.*, c.data AS cl FROM appointments a JOIN clinicians c ON c.id = a.clinician_id WHERE a.ts >= ? AND a.status != 'cancelled'", (today,)):
        out.append({"kind": "appointment", "title": f"Upcoming: {db.unj(a['cl'])['name']}", "body": f"{a['ts'][:16].replace('T', ' ')} · prepare your brief",
                    "route": "/care", "ts": a["ts"]})
    for m in meds(today):
        if m["active"] and m["taken_today"] < len(m["times"]):
            out.append({"kind": "medication", "title": f"{m['name']} — {len(m['times']) - m['taken_today']} dose(s) left today",
                        "body": ", ".join(m["times"]), "route": "/meds", "ts": today})
    read = {r["key"] for r in db.rows("SELECT key FROM notif_read")}
    for n in out:
        n["key"] = f"{n['kind']}:{n['title']}"
        n["read"] = n["key"] in read
    return out

# ------------------------------------------------------------------ clinician notes (Top 3 + TL;DR)

def clinician_notes() -> dict:
    L = engine.latest_values()
    risks = derived.risk_matrix()
    ins = [i for i in engine.list_insights() if i["kind"] == "cross_panel"]
    # Priority = out-of-range markers weighted by evidence grade and how many risks they drive.
    weight = {}
    for r in risks:
        for d in r["drivers"]:
            weight[d["id"]] = weight.get(d["id"], 0) + d["weight"] * (2 if r["level"] == "high" else 1)
    grade = {"A": 1.0, "B": 0.8, "C": 0.5}
    from .catalog_ext import EVIDENCE
    cand = [(w * grade.get(EVIDENCE.get(m, "B"), 0.8), m) for m, w in weight.items() if m in L and L[m]["status"] == "out_of_range"]
    top = []
    for score, m in sorted(cand, reverse=True)[:3]:
        r = L[m]
        related = [x for x in CONCERNS if m in CONCERNS[x]]
        affected = sorted({o for c in related for o in CONCERNS[c] if o != m and o in L and L[o]["status"] == "out_of_range"})[:4]
        t = engine.marker_trend(m)
        top.append({"id": m, "name": MARKERS[m][0], "value": r["value_num"], "unit": r["unit"], "day": r["collected_on"],
                    "trend": t, "why": next((i["title"] for i in ins if any(e.get("marker_id") == m for e in i["evidence"])), None),
                    "related": [{"id": a, "name": MARKERS[a][0]} for a in affected]})
    high = [r["condition"] for r in risks if r["level"] == "high"]
    ok = [r["condition"] for r in risks if r["level"] == "low"]
    n_out = sum(1 for r in L.values() if r["status"] == "out_of_range")
    low = lambda xs: ", ".join(x if x.split(" ")[-1].strip("()").isupper() else x[0].lower() + x[1:] for x in xs)
    tldr = (f"{n_out} of {len(L)} markers are out of range. The clearest themes are {low(high[:4])}"
            f"{' — they share drivers (visceral fat, insulin resistance, inflammation), so the same few changes move all of them' if len(high) > 1 else ''}. "
            f"Reassuring: {low(ok[:3]) or 'none yet'}.")
    return {"top": top, "tldr": tldr, "high": high, "reassuring": ok,
            "disclaimer": "Generated from your Vault by Telomy's engine; not a diagnosis. Items marked for review go to your clinician."}

# ------------------------------------------------------------------ meditation / breathing stats

def session_stats(today: str) -> dict:
    end = date.fromisoformat(today)
    days = []
    for i in range(6, -1, -1):
        d = (end - timedelta(days=i)).isoformat()
        m = db.one("SELECT COALESCE(SUM(minutes),0) AS m FROM sessions_log WHERE substr(ts,1,10) = ?", (d,))["m"]
        days.append({"day": d, "minutes": round(m, 1)})
    total = db.one("SELECT COALESCE(SUM(minutes),0) AS m, COUNT(*) AS n FROM sessions_log")
    streak = 0
    for i in range(0, 365):
        d = (end - timedelta(days=i)).isoformat()
        if db.one("SELECT 1 AS x FROM sessions_log WHERE substr(ts,1,10) = ?", (d,)):
            streak += 1
        else:
            break
    eff = None
    s = dict(engine.series("hrv"))
    sess_days = {r["d"] for r in db.rows("SELECT DISTINCT substr(ts,1,10) AS d FROM sessions_log")}
    after = [s[(date.fromisoformat(d) + timedelta(days=1)).isoformat()] for d in sess_days if (date.fromisoformat(d) + timedelta(days=1)).isoformat() in s]
    if len(after) >= 5:
        base = engine.signal_baseline("hrv", today, 60)
        eff = {"n": len(after), "hrv_after": round(sum(after) / len(after), 1), "baseline": base["mean"] if base else None}
    return {"week": days, "total_minutes": round(total["m"]), "sessions": total["n"], "days_in_a_row": streak, "hrv_effect": eff,
            "recent": db.rows("SELECT * FROM sessions_log ORDER BY ts DESC LIMIT 10")}

# ------------------------------------------------------------------ document intake (prescriptions, discharge summaries)

DOC_TYPES = [("prescription", ["rx", "prescription", "tab.", "tablet", "cap.", "capsule", "od", "bd", "tds", "once daily", "twice daily"]),
             ("discharge", ["discharge summary", "date of admission", "date of discharge", "diagnosis at discharge"]),
             ("imaging", ["impression", "radiology", "findings:"]),
             ("lab", ["reference range", "result", "units"])]

DRUG_PAT = re.compile(r"(?:tab\.?|tablet|cap\.?|capsule|inj\.?)?\s*([A-Z][a-zA-Z\-]+(?:\s[A-Z][a-zA-Z\-]+)?)\s+(\d+(?:\.\d+)?\s?(?:mg|mcg|g|iu|IU|ml))"
                      r"(?:[^\n]*?\b(OD|BD|TDS|QID|HS|once daily|twice daily|at night|morning))?", re.I)


def classify_document(text: str) -> str:
    t = text.lower()
    scores = {k: sum(t.count(w) for w in ws) for k, ws in DOC_TYPES}
    return max(scores, key=scores.get) if any(scores.values()) else "other"


def extract_meds(text: str) -> list[dict]:
    out, seen = [], set()
    for name, dose, freq in DRUG_PAT.findall(text):
        key = name.lower()
        if key in seen or key in ("result", "reference", "patient"):
            continue
        seen.add(key)
        times = {"bd": ["08:00", "20:00"], "twice daily": ["08:00", "20:00"], "tds": ["08:00", "14:00", "20:00"],
                 "hs": ["22:00"], "at night": ["22:00"]}.get((freq or "").lower(), ["08:00"])
        out.append({"name": name.strip(), "dose": dose.replace(" ", ""), "frequency": freq or "once daily", "times": times})
    return out
