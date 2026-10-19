"""Wellness-centre operations — members, memberships, resource-aware scheduling, check-in and invoices. Everything is
driven by the platform config (platform.py): services come from the `service_type` catalog, memberships from
`membership_plan`, rooms/devices from `resource`, and every entity carries the org's custom fields. So a centre shapes
its own catalog, forms and pricing without code.

Patterned on the modules of multi-location wellness platforms (scheduling with rooms/resources, membership entitlements
and recurring billing, check-in, outcomes) but modular: a centre turns modules on/off and the screens follow.
"""
import time
from datetime import date, datetime, timedelta

from . import db, platform

SCHEMA = """
CREATE TABLE IF NOT EXISTS c_members (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, name TEXT, phone TEXT, email TEXT,
  patient_id INTEGER, joined_on TEXT, status TEXT DEFAULT 'active', fields TEXT);
CREATE TABLE IF NOT EXISTS c_memberships (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, member_id INTEGER, plan_id INTEGER,
  started_on TEXT, ends_on TEXT, status TEXT DEFAULT 'active', credits_total INTEGER, credits_used INTEGER DEFAULT 0, data TEXT);
CREATE TABLE IF NOT EXISTS c_bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, member_id INTEGER, service_id INTEGER,
  staff_id INTEGER, resource_id INTEGER, start_ts TEXT, minutes INTEGER, status TEXT DEFAULT 'booked', price INTEGER, fields TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_c_bookings ON c_bookings(org, start_ts);
CREATE TABLE IF NOT EXISTS c_invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, member_id INTEGER, ts TEXT,
  lines TEXT, total INTEGER, status TEXT DEFAULT 'due', method TEXT);
"""


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ---- members ----------------------------------------------------------------------------------------------------

def add_member(org: str, name: str, phone: str = "", email: str = "", patient_id: int | None = None, fields: dict | None = None) -> dict:
    if not name.strip():
        raise ValueError("name is required")
    vals = platform.validate_values(org, "member", fields or {})
    mid = db.exec_("INSERT INTO c_members (org, name, phone, email, patient_id, joined_on, status, fields) VALUES (?,?,?,?,?,?,?,?)",
                   (org, name.strip(), phone, email, patient_id, date.today().isoformat(), "active", db.j(vals)))
    return member(mid)


def member(mid: int) -> dict | None:
    r = db.one("SELECT * FROM c_members WHERE id = ?", (mid,))
    if not r:
        return None
    ms = db.rows("SELECT * FROM c_memberships WHERE member_id = ? AND status = 'active' ORDER BY id DESC", (mid,))
    return {**r, "fields": db.unj(r["fields"], {}), "memberships": [_ms(m) for m in ms]}


def list_members(org: str) -> list[dict]:
    return [{**r, "fields": db.unj(r["fields"], {})} for r in db.rows("SELECT * FROM c_members WHERE org = ? ORDER BY name", (org,))]


# ---- memberships ------------------------------------------------------------------------------------------------

def _ms(r: dict) -> dict:
    return {**r, "data": db.unj(r["data"], {}), "credits_left": (r["credits_total"] - r["credits_used"]) if r["credits_total"] else None}


def enroll(org: str, member_id: int, plan_id: int) -> dict:
    plan = platform.catalog_item(plan_id)
    if not plan or plan["kind"] != "membership_plan":
        raise ValueError("no such membership plan")
    d = plan["data"]
    cycle_days = int(d.get("cycle_days", 30))
    ends = (date.today() + timedelta(days=cycle_days)).isoformat()
    mid = db.exec_("""INSERT INTO c_memberships (org, member_id, plan_id, started_on, ends_on, status, credits_total, credits_used, data)
                      VALUES (?,?,?,?,?,?,?,0,?)""",
                   (org, member_id, plan_id, date.today().isoformat(), ends, "active", d.get("credits"), db.j({"plan": plan["name"], "price": d.get("price")})))
    # an invoice for the plan price
    if d.get("price"):
        add_invoice(org, member_id, [{"desc": f"Membership — {plan['name']}", "amount": d["price"]}])
    return _ms(db.one("SELECT * FROM c_memberships WHERE id = ?", (mid,)))


def freeze(ms_id: int, on: bool) -> dict:
    db.exec_("UPDATE c_memberships SET status = ? WHERE id = ?", ("frozen" if on else "active", ms_id))
    return _ms(db.one("SELECT * FROM c_memberships WHERE id = ?", (ms_id,)))


# ---- scheduling (resource-aware) --------------------------------------------------------------------------------

def _overlaps(org: str, start: datetime, minutes: int, resource_id: int | None, staff_id: int | None, exclude: int | None = None):
    end = start + timedelta(minutes=minutes)
    rows = db.rows("SELECT * FROM c_bookings WHERE org = ? AND status NOT IN ('cancelled','no_show')", (org,))
    for b in rows:
        if exclude and b["id"] == exclude:
            continue
        bs = datetime.fromisoformat(b["start_ts"]); be = bs + timedelta(minutes=b["minutes"] or 0)
        if bs < end and start < be:
            if resource_id and b["resource_id"] == resource_id:
                return f"that room/resource is booked {bs.strftime('%H:%M')}–{be.strftime('%H:%M')}"
            if staff_id and b["staff_id"] == staff_id:
                return f"that staff member is booked {bs.strftime('%H:%M')}–{be.strftime('%H:%M')}"
    return None


def book(org: str, member_id: int, service_id: int, start_ts: str, staff_id: int | None = None, resource_id: int | None = None,
         fields: dict | None = None) -> dict:
    svc = platform.catalog_item(service_id)
    if not svc or svc["kind"] != "service_type":
        raise ValueError("no such service")
    minutes = int(svc["data"].get("minutes", 60))
    price = int(svc["data"].get("price", 0))
    start = datetime.fromisoformat(start_ts)
    clash = _overlaps(org, start, minutes, resource_id, staff_id)
    if clash:
        raise ValueError(clash)
    vals = platform.validate_values(org, "booking", fields or {})
    bid = db.exec_("""INSERT INTO c_bookings (org, member_id, service_id, staff_id, resource_id, start_ts, minutes, status, price, fields, created_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                   (org, member_id, service_id, staff_id, resource_id, start_ts, minutes, "booked", price, db.j(vals), time.time()))
    return booking(bid)


def booking(bid: int) -> dict | None:
    r = db.one("SELECT * FROM c_bookings WHERE id = ?", (bid,))
    if not r:
        return None
    svc = platform.catalog_item(r["service_id"])
    return {**r, "fields": db.unj(r["fields"], {}), "service_name": svc["name"] if svc else None}


def schedule(org: str, day: str | None = None) -> list[dict]:
    day = day or date.today().isoformat()
    rows = db.rows("SELECT * FROM c_bookings WHERE org = ? AND substr(start_ts,1,10) = ? ORDER BY start_ts", (org, day))
    return [booking(r["id"]) for r in rows]


def check_in(bid: int) -> dict:
    b = booking(bid)
    if not b:
        raise ValueError("no such booking")
    db.exec_("UPDATE c_bookings SET status = 'checked_in' WHERE id = ?", (bid,))
    # spend a membership credit if the member has one
    ms = db.one("SELECT * FROM c_memberships WHERE member_id = ? AND status = 'active' AND credits_total IS NOT NULL AND credits_used < credits_total ORDER BY id", (b["member_id"],))
    if ms:
        db.exec_("UPDATE c_memberships SET credits_used = credits_used + 1 WHERE id = ?", (ms["id"],))
    elif b["price"]:
        add_invoice(b["org"], b["member_id"], [{"desc": b.get("service_name") or "Service", "amount": b["price"]}])
    return booking(bid)


def set_status(bid: int, status: str) -> dict:
    if status not in ("booked", "checked_in", "completed", "cancelled", "no_show"):
        raise ValueError("bad status")
    db.exec_("UPDATE c_bookings SET status = ? WHERE id = ?", (status, bid))
    return booking(bid)


# ---- invoices ---------------------------------------------------------------------------------------------------

def add_invoice(org: str, member_id: int, lines: list[dict], method: str | None = None) -> dict:
    total = sum(int(l.get("amount", 0)) for l in lines)
    iid = db.exec_("INSERT INTO c_invoices (org, member_id, ts, lines, total, status, method) VALUES (?,?,?,?,?,?,?)",
                   (org, member_id, datetime.now().isoformat(), db.j(lines), total, "paid" if method else "due", method))
    return invoice(iid)


def invoice(iid: int) -> dict:
    r = db.one("SELECT * FROM c_invoices WHERE id = ?", (iid,))
    return {**r, "lines": db.unj(r["lines"], [])} if r else None


def pay(iid: int, method: str) -> dict:
    db.exec_("UPDATE c_invoices SET status = 'paid', method = ? WHERE id = ?", (method, iid))
    return invoice(iid)


# ---- dashboard --------------------------------------------------------------------------------------------------

def dashboard(org: str = "default", day: str | None = None) -> dict:
    day = day or date.today().isoformat()
    sched = schedule(org, day)
    members = db.one("SELECT COUNT(*) AS n FROM c_members WHERE org = ? AND status = 'active'", (org,))["n"]
    due = db.one("SELECT COALESCE(SUM(total),0) AS t FROM c_invoices WHERE org = ? AND status = 'due'", (org,))["t"]
    revenue = db.one("SELECT COALESCE(SUM(total),0) AS t FROM c_invoices WHERE org = ? AND status = 'paid' AND substr(ts,1,10) = ?", (org, day))["t"]
    return {"org": org, "day": day, "modules": platform.enabled_modules(org), "active_members": members,
            "today_bookings": len(sched), "checked_in": sum(1 for b in sched if b["status"] in ("checked_in", "completed")),
            "revenue_today": revenue, "outstanding": due, "schedule": sched}
