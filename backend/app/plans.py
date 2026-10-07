"""Plans, monthly doctor reports and on-demand consultations.

Pricing benchmarks (Oct 2026): Practo online GP ₹799; Practo Plus ₹1,199/month; Function Health $365/yr and
Superpower $349/yr (US, clinician-reviewed report); Ultrahuman Blood Vision annual $499.
Payments run in TEST MODE — nothing is charged.
"""
from datetime import date, datetime, timedelta

from . import db, derived, engine, features, predict

PLANS = [
    {"id": "free", "name": "Free", "price_month": 0, "price_year": 0,
     "features": ["Vault: labs, imaging, wearables", "Report reading & verification", "Disease-risk predictions",
                  "Sinc quick answers"], "monthly_report": None, "consults_month": 0, "specialist_quarter": 0},
    {"id": "essential", "name": "Essential", "price_month": 499, "price_year": 4999,
     "features": ["Everything in Free", "Monthly AI health report", "Sinc Deep Research with citations", "N-of-1 studies",
                  "Specialist packs (PDF + FHIR)"], "monthly_report": "ai", "consults_month": 0, "specialist_quarter": 0},
    {"id": "plus", "name": "Plus", "price_month": 1499, "price_year": 14999, "popular": True,
     "features": ["Everything in Essential", "Monthly report reviewed and signed by a doctor (within 72 h)",
                  "1 doctor consultation a month (video or chat)", "Sinc medical drafts signed off by your doctor"],
     "monthly_report": "doctor", "consults_month": 1, "specialist_quarter": 0},
    {"id": "pro", "name": "Longevity Pro", "price_month": 3999, "price_year": 39999,
     "features": ["Everything in Plus", "Unlimited GP consultations", "2 specialist consultations a quarter",
                  "2 longevity blood panels a year", "Annual DEXA and VO2 max test", "Named longevity physician"],
     "monthly_report": "doctor", "consults_month": 99, "specialist_quarter": 2},
]
ON_DEMAND = {"gp": {"name": "General physician", "price": 699, "minutes": 15},
             "specialist": {"name": "Specialist", "price": 1499, "minutes": 20},
             "longevity": {"name": "Longevity physician", "price": 1999, "minutes": 30}}
CENTRE_PLANS = [
    {"id": "centre_starter", "name": "Centre Starter", "price_month": 14999, "members": 100, "doctor_seats": 1},
    {"id": "centre_growth", "name": "Centre Growth", "price_month": 39999, "members": 500, "doctor_seats": 3},
    {"id": "centre_enterprise", "name": "Enterprise", "price_month": None, "members": None, "doctor_seats": None},
]
DOCTOR_SEAT = 2999

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (id INTEGER PRIMARY KEY CHECK (id = 1), plan TEXT, billing TEXT, since TEXT, renews TEXT);
CREATE TABLE IF NOT EXISTS monthly_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT UNIQUE, created_at TEXT,
  state TEXT, data TEXT, doctor TEXT, doctor_note TEXT, signed_at TEXT);
CREATE TABLE IF NOT EXISTS consults (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, mode TEXT, reason TEXT, requested_at TEXT,
  scheduled_at TEXT, doctor TEXT, status TEXT, price INTEGER, covered INTEGER, notes TEXT);
"""


def _pred_row(v: dict) -> dict:
    row = {x: v.get(x) for x in ("risk", "band", "score", "model")}
    if row["risk"] is None and (v.get("ten_year") or {}).get("total_cvd") is not None:  # PREVENT reports 10- and 30-year totals
        row["risk"], row["band"] = v["ten_year"]["total_cvd"], f"10-year total CVD · 30-year {v['thirty_year']['total_cvd']}%"
    return row


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def plan_by_id(pid):
    return next((p for p in PLANS if p["id"] == pid), PLANS[0])


def subscription() -> dict:
    s = db.one("SELECT * FROM subscriptions WHERE id = 1") or {"plan": "free", "billing": None, "since": None, "renews": None}
    p = plan_by_id(s["plan"])
    month = (engine.last_signal_day() or date.today().isoformat())[:7]
    used = db.one("SELECT COUNT(*) AS n FROM consults WHERE covered = 1 AND substr(requested_at,1,7) = ? AND status != 'cancelled'", (month,))["n"]
    return {**s, "plan_detail": p, "consults_used_month": used, "consults_left_month": max(0, p["consults_month"] - used)}


def subscribe(plan_id: str, billing: str, today: str) -> dict:
    if plan_id not in {p["id"] for p in PLANS}:
        raise ValueError("Unknown plan")
    renews = (date.fromisoformat(today) + timedelta(days=365 if billing == "year" else 30)).isoformat()
    db.exec_("INSERT OR REPLACE INTO subscriptions (id, plan, billing, since, renews) VALUES (1,?,?,?,?)", (plan_id, billing, today, renews))
    p = plan_by_id(plan_id)
    price = p["price_year"] if billing == "year" else p["price_month"]
    return {**subscription(), "message": f"You're on {p['name']}. Test mode: ₹{price:,} was not charged."}


# --------------------------------------------------------------------------- monthly report

def _month_bounds(period: str):
    y, m = map(int, period.split("-"))
    start = date(y, m, 1)
    end = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    return start, end


def generate_monthly(period: str) -> dict:
    """Auto-generated each month. Free → not available; Essential → AI report; Plus/Pro → AI draft queued for a doctor."""
    sub = subscription()
    kind = sub["plan_detail"]["monthly_report"]
    if not kind:
        raise PermissionError("Monthly reports are part of Essential and above.")
    start, end = _month_bounds(period)
    prev_start = (start - timedelta(days=1)).replace(day=1)
    s, e, ps, pe = start.isoformat(), end.isoformat(), prev_start.isoformat(), (start - timedelta(days=1)).isoformat()

    def avg(metric, a, b):
        v = [x for _, x in engine.series(metric, a, b)]
        return round(sum(v) / len(v), 1) if v else None
    signals = []
    for m in ("hrv", "rhr", "sleep_hours", "deep_sleep", "steps", "sbp", "vo2max", "weight"):
        cur, prev = avg(m, s, e), avg(m, ps, pe)
        if cur is None:
            continue
        lab, unit, better, dec = engine.SIGNALS[m]
        if not dec:
            cur, prev = round(cur), (round(prev) if prev is not None else None)
        d = None if prev is None else round(cur - prev, dec or 0)
        verdict = None if d is None or better == "mid" else ("better" if (d > 0) == (better == "high") else "worse") if d else "same"
        signals.append({"id": m, "label": lab, "unit": unit, "this_month": cur, "last_month": prev, "change": d, "verdict": verdict})
    new_reports = db.rows("SELECT id, title, panel, collected_on FROM reports WHERE collected_on BETWEEN ? AND ?", (s, e))
    events = db.rows("SELECT kind, COUNT(*) AS n FROM events WHERE substr(ts,1,10) BETWEEN ? AND ? GROUP BY kind ORDER BY n DESC", (s, e))
    meds = features.meds(e)
    notes = features.clinician_notes()
    pred = predict.run(predict.inputs_from_vault())["models"]
    checks = db.one("SELECT COUNT(*) AS n FROM checklist WHERE done = 1 AND day BETWEEN ? AND ?", (s, e))["n"]
    plan_items = sum(len(v) for v in (db.unj((db.one("SELECT data FROM protocols WHERE active = 1") or {"data": "{}"})["data"], {}).get("pillars") or {}).values())
    days = (min(end, date.fromisoformat(engine.last_signal_day())) - start).days + 1
    adherence = round(100 * checks / max(plan_items * days, 1))
    wins = [x for x in signals if x["verdict"] == "better"]
    watch = [x for x in signals if x["verdict"] == "worse"]
    summary = (f"In {start.strftime('%B %Y')} {len(wins)} of your tracked signals improved and {len(watch)} moved the wrong way. "
               f"{len(new_reports)} new report(s) were added. Your top priorities remain {', '.join(t['name'] for t in notes['top'][:3])}.")
    actions = []
    if any(x["id"] == "hrv" and x["verdict"] == "worse" for x in signals):
        actions.append("HRV fell this month — alcohol and hard-workout days are your two strongest drags; space them out.")
    if pred["diabetes"].get("risk") and pred["diabetes"]["risk"] >= 15:
        actions.append(f"5-year diabetes risk is {pred['diabetes']['risk']}% — post-meal walks and protein-first breakfasts are the levers.")
    for t in notes["top"][:2]:
        actions.append(f"Retest {t['name']} as planned and keep the action plan going.")
    data = {"period": period, "range": [s, e], "summary": summary, "signals": signals, "new_reports": new_reports,
            "events": events, "medications": [{"name": m["name"], "adherence": m["adherence_30d"]} for m in meds if m["active"]],
            "protocol_adherence": adherence, "priorities": notes["top"], "predictions": {k: _pred_row(v) for k, v in pred.items()},
            "actions": actions, "kind": kind}
    state = "awaiting_doctor" if kind == "doctor" else "ready"
    db.exec_("""INSERT INTO monthly_reports (period, created_at, state, data) VALUES (?,?,?,?)
                ON CONFLICT(period) DO UPDATE SET data = excluded.data, created_at = excluded.created_at,
                state = CASE WHEN monthly_reports.state = 'signed' THEN 'signed' ELSE excluded.state END""",
             (period, engine.now_iso(), state, db.j(data)))
    return get_monthly(period)


def get_monthly(period: str) -> dict | None:
    r = db.one("SELECT * FROM monthly_reports WHERE period = ?", (period,))
    if not r:
        return None
    r["data"] = db.unj(r["data"], {})
    return r


def list_monthly() -> list[dict]:
    rs = db.rows("SELECT id, period, created_at, state, doctor, signed_at FROM monthly_reports ORDER BY period DESC")
    return rs


def sign_monthly(period: str, doctor: str, note: str) -> dict:
    r = get_monthly(period)
    if not r:
        raise LookupError("No report for that month")
    if not note.strip():
        raise ValueError("Add a short note for the patient before signing.")
    db.exec_("UPDATE monthly_reports SET state = 'signed', doctor = ?, doctor_note = ?, signed_at = ? WHERE period = ?",
             (doctor, note.strip(), engine.now_iso(), period))
    return get_monthly(period)


# --------------------------------------------------------------------------- consultations on demand

DOCTORS = {"gp": "Dr. Meera Rao", "specialist": "Dr. Kavya Iyer", "longevity": "Dr. Meera Rao"}


def request_consult(kind: str, mode: str, reason: str, today: str) -> dict:
    if kind not in ON_DEMAND:
        raise ValueError("Unknown consultation type")
    if mode not in ("video", "chat", "audio"):
        raise ValueError("Choose video, audio or chat")
    sub = subscription()
    p = sub["plan_detail"]
    covered = (kind == "gp" and sub["consults_left_month"] > 0) or (kind in ("gp", "longevity") and p["id"] == "pro")
    price = 0 if covered else ON_DEMAND[kind]["price"]
    # Both timestamps use the app clock (today + wall time) so the slot is always after the request.
    requested = datetime.fromisoformat(today + engine.now_iso()[10:])
    if kind == "gp":
        slot = requested + timedelta(minutes=30)
        slot = slot.replace(minute=0 if slot.minute < 30 else 30, second=0) + timedelta(minutes=30)
    else:
        slot = (requested + timedelta(days=1)).replace(hour=10, minute=0, second=0)
    when = slot.isoformat(timespec="minutes")
    cid = db.exec_("""INSERT INTO consults (kind, mode, reason, requested_at, scheduled_at, doctor, status, price, covered)
                      VALUES (?,?,?,?,?,?,?,?,?)""", (kind, mode, reason, requested.isoformat(timespec="seconds"), when,
                                                      DOCTORS[kind], "scheduled", price, 1 if covered else 0))
    msg = (f"{ON_DEMAND[kind]['name']} {mode} consult with {DOCTORS[kind]} at {when.replace('T', ' ')}. "
           + ("Covered by your plan." if covered else f"₹{price} — test mode, not charged.") + " Your pre-clinic brief is attached.")
    return {"id": cid, "message": msg, "covered": covered, "price": price, "scheduled_at": when, "doctor": DOCTORS[kind]}


def consults() -> list[dict]:
    return db.rows("SELECT * FROM consults ORDER BY requested_at DESC")


def complete_consult(cid: int, notes: str) -> dict:
    if not notes.strip():
        raise ValueError("Consult notes are required to complete.")
    db.exec_("UPDATE consults SET status = 'completed', notes = ? WHERE id = ?", (notes.strip(), cid))
    return db.one("SELECT * FROM consults WHERE id = ?", (cid,))
