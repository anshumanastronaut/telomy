"""Custom activities — a fast bowler's spell, a round of golf, a padel match, a long drive — created manually or by voice.

Each activity gets its own measurement environment:
  • standard vitals captured during the activity (heart rate, HRV, breathing, skin temperature from the watch/band/patch),
  • activity-specific fields the person defines (overs, deliveries, ball speed; holes, strokes, putts),
  • derived scores (golf: calm index from HR stability and HRV; bowling: workload, HR recovery between spells),
  • personal baselines (median ± MAD of the last 10 sessions), longitudinal trends, and links to readiness (prior-night
    HRV and sleep) and to next-day recovery — so a bowler sees which nights produce his fastest spells, and a golfer sees
    how calm he stays as the round goes on.
"""
import math
import random
import re
from datetime import date, datetime, timedelta

from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_types (id TEXT PRIMARY KEY, name TEXT, category TEXT, fields TEXT, scores TEXT, created_at TEXT, created_by TEXT);
CREATE TABLE IF NOT EXISTS activity_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, type_id TEXT, ts TEXT, minutes REAL, values_json TEXT,
  vitals TEXT, notes TEXT, source TEXT);
"""

TEMPLATES = {
    "fast_bowling": {"name": "Fast bowling (cricket)", "category": "Sport", "scores": ["workload", "hr_recovery"],
                     "fields": [("overs", "Overs bowled", "overs"), ("deliveries", "Deliveries", ""), ("max_speed", "Fastest ball", "km/h"),
                                ("avg_speed", "Average speed", "km/h"), ("wickets", "Wickets", ""), ("rpe", "Effort (RPE 1–10)", "")]},
    "golf": {"name": "Golf round", "category": "Sport", "scores": ["calm_index", "pressure_hr"],
             "fields": [("holes", "Holes", ""), ("strokes", "Strokes", ""), ("putts", "Putts", ""), ("fairways", "Fairways hit", ""),
                        ("calm_self", "How calm I felt (1–10)", "")]},
    "running": {"name": "Running", "category": "Endurance", "scores": ["efficiency"],
                "fields": [("km", "Distance", "km"), ("pace", "Pace", "min/km"), ("rpe", "Effort (RPE 1–10)", "")]},
    "strength": {"name": "Strength session", "category": "Strength", "scores": ["workload"],
                 "fields": [("sets", "Sets", ""), ("tonnage", "Total load", "kg"), ("rpe", "Effort (RPE 1–10)", "")]},
    "meditation": {"name": "Meditation", "category": "Mind", "scores": ["calm_index"], "fields": [("minutes", "Minutes", "min")]},
}
VOICE_MAP = {"bowl": "fast_bowling", "bowled": "fast_bowling", "bowling": "fast_bowling", "bowling spell": "fast_bowling", "nets": "fast_bowling",
             "golf": "golf", "round of golf": "golf", "ran": "running", "run": "running", "running": "running", "gym": "strength",
             "lifted": "strength", "meditation": "meditation"}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def create_type(name: str, fields: list[dict] | None = None, template: str | None = None, by: str = "manual") -> dict:
    if template and template in TEMPLATES:
        t = TEMPLATES[template]
        tid, nm, cat, flds, scores = template, t["name"], t["category"], [{"key": k, "label": l, "unit": u} for k, l, u in t["fields"]], t["scores"]
    else:
        if not name.strip():
            raise ValueError("Give the activity a name.")
        tid = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]
        nm, cat, flds, scores = name.strip(), "Custom", fields or [{"key": "rpe", "label": "Effort (RPE 1–10)", "unit": ""}], ["calm_index", "workload"]
    db.exec_("INSERT OR REPLACE INTO activity_types (id, name, category, fields, scores, created_at, created_by) VALUES (?,?,?,?,?,?,?)",
             (tid, nm, cat, db.j(flds), db.j(scores), engine.now_iso(), by))
    return get_type(tid)


def get_type(tid: str) -> dict | None:
    r = db.one("SELECT * FROM activity_types WHERE id = ?", (tid,))
    if r:
        r["fields"], r["scores"] = db.unj(r["fields"], []), db.unj(r["scores"], [])
    return r


def _vitals_from_hr(hr: list[float], hrv: list[float]) -> dict:
    """Session vitals summary from a per-minute HR/HRV series (watch, band or patch)."""
    if not hr:
        return {}
    m = sum(hr) / len(hr)
    sd = (sum((x - m) ** 2 for x in hr) / max(1, len(hr) - 1)) ** 0.5
    succ = [abs(b - a) for a, b in zip(hr, hr[1:])]
    out = {"hr_mean": round(m, 1), "hr_max": round(max(hr)), "hr_sd": round(sd, 1), "hr_mssd": round(sum(succ) / max(1, len(succ)), 1),
           "hrv_mean": round(sum(hrv) / len(hrv), 1) if hrv else None, "minutes": len(hr)}
    # calm index: steadier heart rate and higher HRV relative to the person's resting values → calmer (0–100)
    rest = engine.signal_baseline("rhr", days=30)
    rest_hrv = engine.signal_baseline("hrv", days=30)
    if rest and hrv and rest_hrv:
        arousal = (m - rest["mean"]) / 25 + sd / 12 - (out["hrv_mean"] - 0.6 * rest_hrv["mean"]) / 20
        out["calm_index"] = round(100 / (1 + math.exp(1.5 * arousal - 0.5)))
    return out


def log_session(tid: str, values: dict, minutes: float | None = None, hr: list[float] | None = None, hrv: list[float] | None = None,
                ts: str | None = None, notes: str = "", source: str = "manual") -> dict:
    t = get_type(tid)
    if not t:
        raise LookupError("Unknown activity")
    vit = _vitals_from_hr(hr or [], hrv or [])
    if tid == "fast_bowling" and values.get("deliveries"):
        vit["workload"] = round(values["deliveries"] * (values.get("rpe") or 6) / 10, 1)
    if tid == "golf" and hr:
        holes = int(values.get("holes") or 18)
        per = max(1, len(hr) // holes)
        vit["hole_hr"] = [round(sum(hr[i:i + per]) / len(hr[i:i + per]), 1) for i in range(0, per * holes, per)][:holes]
        vit["pressure_hr"] = round(max(vit["hole_hr"][-3:]) - min(vit["hole_hr"][:3]), 1) if len(vit["hole_hr"]) >= 6 else None
    sid = db.exec_("INSERT INTO activity_sessions (type_id, ts, minutes, values_json, vitals, notes, source) VALUES (?,?,?,?,?,?,?)",
                   (tid, ts or engine.now_iso(), minutes or vit.get("minutes"), db.j(values), db.j(vit), notes, source))
    db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)",
             (ts or engine.now_iso(), f"activity:{tid}", t["name"], None, db.j({"session_id": sid})))
    return {"id": sid, "vitals": vit}


def log_from_voice(it: dict) -> dict:
    tid = VOICE_MAP.get(it["activity"])
    if not tid:
        tid = re.sub(r"[^a-z0-9]+", "_", it["activity"])[:40]
    if not get_type(tid):
        create_type(it["activity"].title(), template=tid if tid in TEMPLATES else None, by="voice")
    vals = {}
    t = it.get("text", "").lower()
    for key, rx in (("overs", r"(\d+(?:\.\d)?)\s*overs?"), ("max_speed", r"(\d{2,3})\s*(?:km/?h|kmph|clicks)"), ("wickets", r"(\d+)\s*wickets?"),
                    ("strokes", r"shot\s*(\d{2,3})|(\d{2,3})\s*strokes"), ("holes", r"(\d{1,2})\s*holes"), ("km", r"(\d+(?:\.\d+)?)\s*(?:km|k)\b")):
        m = re.search(rx, t)
        if m:
            vals[key] = float(next(g for g in m.groups() if g))
    if "overs" in vals:
        vals["deliveries"] = int(vals["overs"]) * 6 + round((vals["overs"] % 1) * 10)
    r = log_session(tid, vals, it.get("minutes"), ts=it.get("ts"), notes=it.get("text", ""), source="voice")
    return {"activity": tid, "session_id": r["id"], "message": f"Logged {get_type(tid)['name']}" + (f" — {', '.join(f'{k} {v:g}' for k, v in vals.items())}" if vals else "") + "."}


def _baseline(vals: list[float]) -> dict | None:
    v = [x for x in vals if x is not None][-10:]
    if len(v) < 3:
        return None
    s = sorted(v)
    med = s[len(s) // 2]
    mad = sorted(abs(x - med) for x in v)[len(v) // 2] or 1e-9
    return {"median": round(med, 1), "mad": round(mad, 1), "n": len(v)}


def detail(tid: str) -> dict:
    t = get_type(tid)
    if not t:
        raise LookupError("Unknown activity")
    ss = db.rows("SELECT * FROM activity_sessions WHERE type_id = ? ORDER BY ts", (tid,))
    for s in ss:
        s["values"], s["vitals"] = db.unj(s["values_json"], {}), db.unj(s["vitals"], {})
    keys = [f["key"] for f in t["fields"]] + ["hr_mean", "hr_max", "hrv_mean", "calm_index", "workload", "pressure_hr"]
    series = {}
    for k in keys:
        pts = [(s["ts"][:10], (s["values"].get(k) if k in s["values"] else s["vitals"].get(k))) for s in ss]
        pts = [(d, v) for d, v in pts if isinstance(v, (int, float))]
        if pts:
            first, last = pts[0][1], pts[-1][1]
            series[k] = {"points": pts, "baseline": _baseline([v for _, v in pts]), "first": first, "last": last,
                         "change": round(last - first, 1), "latest_vs_baseline": None}
            b = series[k]["baseline"]
            if b:
                series[k]["latest_vs_baseline"] = round((last - b["median"]) / (1.4826 * max(b["mad"], 0.05)), 1)
    insights = _insights(t, ss, series)
    return {"type": t, "sessions": [{k: s[k] for k in ("id", "ts", "minutes", "values", "vitals", "notes", "source")} for s in ss][::-1],
            "series": series, "insights": insights}


def _insights(t, ss, series) -> list[str]:
    out = []
    if len(ss) < 4:
        return [f"{len(ss)} session{'s' if len(ss) != 1 else ''} so far — Telomy builds your baselines after 4."]
    hrv = dict(engine.series("hrv"))
    sleep = dict(engine.series("sleep_hours"))
    perf_key = "max_speed" if t["id"] == "fast_bowling" else "strokes" if t["id"] == "golf" else "calm_index" if "calm_index" in series else None
    if perf_key and perf_key in series:
        pairs = []
        for s in ss:
            v = s["values"].get(perf_key, s["vitals"].get(perf_key))
            d = s["ts"][:10]
            if v is not None and d in hrv:
                pairs.append((hrv[d], v, sleep.get(d)))
        if len(pairs) >= 5:
            r, p = engine.pearson([a for a, _, _ in pairs], [b for _, b, _ in pairs])
            nice = {"max_speed": "fastest ball", "strokes": "score (strokes)", "calm_index": "calm index"}[perf_key]
            hi = [b for a, b, _ in pairs if a >= sorted(x for x, _, _ in pairs)[len(pairs) // 2]]
            lo = [b for a, b, _ in pairs if a < sorted(x for x, _, _ in pairs)[len(pairs) // 2]]
            if hi and lo:
                out.append(f"On mornings with above-median HRV your {nice} averaged {sum(hi) / len(hi):.1f} vs {sum(lo) / len(lo):.1f} on low-HRV mornings "
                           f"(r = {r:+.2f}, {engine.fmt_p(p)}, n = {len(pairs)}).")
    if "calm_index" in series and series["calm_index"]["baseline"]:
        c = series["calm_index"]
        out.append(f"Calm index {c['last']:.0f} last time vs your baseline {c['baseline']['median']:.0f} — trend {c['change']:+.0f} since your first session.")
    if t["id"] == "golf" and "pressure_hr" in series:
        out.append(f"Heart rate on the closing holes runs {series['pressure_hr']['baseline']['median'] if series['pressure_hr']['baseline'] else series['pressure_hr']['last']:+.0f} bpm "
                   f"above the opening holes — that is your pressure response; breathing at 6/min between shots lowers it.")
    if t["id"] == "fast_bowling" and "workload" in series:
        w = [v for _, v in series["workload"]["points"]][-4:]
        chronic = sum(w) / len(w)
        acute = w[-1]
        ratio = acute / chronic if chronic else 1
        out.append(f"Acute:chronic workload {ratio:.2f} (last spell vs 4-session average). Fast bowlers' injury risk rises above ~1.5 (Hulin 2014, BJSM).")
    return out


def overview() -> list[dict]:
    out = []
    for t in db.rows("SELECT * FROM activity_types ORDER BY created_at"):
        n = db.one("SELECT COUNT(*) AS n, MAX(ts) AS last FROM activity_sessions WHERE type_id = ?", (t["id"],))
        out.append({"id": t["id"], "name": t["name"], "category": t["category"], "sessions": n["n"], "last": n["last"], "created_by": t["created_by"]})
    return out


def seed(today: date):
    """Two example activities for the test profile: weekly bowling nets and fortnightly golf (fictitious data)."""
    init()
    rnd = random.Random(21)
    create_type("", template="fast_bowling", by="manual")
    create_type("", template="golf", by="voice")
    hrv = dict(engine.series("hrv"))
    base = engine.signal_baseline("hrv", days=90)["mean"]
    for k in range(12):
        d = today - timedelta(days=4 + 7 * k)
        state = (hrv.get(d.isoformat(), base) - base) / 8
        overs = rnd.choice([4, 5, 6, 6, 7])
        hr = [rnd.gauss(118 + 22 * math.sin(i / 3), 6) for i in range(overs * 6)]
        log_session("fast_bowling", {"overs": overs, "deliveries": overs * 6, "max_speed": round(131 + 3.2 * state + rnd.gauss(0, 1.6), 1),
                                     "avg_speed": round(124 + 2.5 * state + rnd.gauss(0, 1.2), 1), "wickets": rnd.choice([0, 1, 1, 2, 3]), "rpe": rnd.choice([6, 7, 7, 8])},
                    overs * 6, hr, [max(8, rnd.gauss(22, 5)) for _ in hr], ts=f"{d.isoformat()}T17:00:00", source="manual")
    for k in range(8):
        d = today - timedelta(days=2 + 14 * k)
        state = (hrv.get(d.isoformat(), base) - base) / 8
        hr = [rnd.gauss(92 + 0.35 * i / 4 - 4 * state - 0.4 * (8 - k), 4) for i in range(18 * 13)]  # gets calmer over the season
        log_session("golf", {"holes": 18, "strokes": round(94 - 1.6 * state + 0.5 * k + rnd.gauss(0, 2)), "putts": rnd.randint(31, 38),
                             "fairways": rnd.randint(5, 10), "calm_self": rnd.randint(5, 8)},
                    240, hr, [max(10, rnd.gauss(30 + 3 * state + 0.6 * (8 - k), 5)) for _ in hr], ts=f"{d.isoformat()}T07:00:00", source="watch")
