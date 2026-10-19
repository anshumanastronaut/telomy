"""Fulfillment & logistics — orders for curated supplements, medicines, and the pickup of test samples, with delivery to
the customer and status tracking. Connects the centre/clinic side to the Telomy Rx engine (supplements/medicines) and
labs (sample collection), so an order flows: created → confirmed → dispatched/collected → in transit → delivered.

Order kinds:
  * supplement  — Telomy Formulas / curated nutraceuticals (from rx.py), delivered to the customer.
  * medicine    — prescription items dispensed by a licensed pharmacy partner against a signed Rx (rx.py plan).
  * lab_sample  — a phlebotomist/pickup for a blood/urine sample collected from the customer and taken to the lab.
  * retail/device/other — anything the centre sells.

Modular: a centre/clinic configures its own couriers/partners via the platform catalog; medicines always require a
signed prescription (enforced), mirroring the Rx safety model.
"""
import time
from datetime import date, datetime, timedelta

from . import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, kind TEXT, member_id INTEGER,
  patient_id INTEGER, rx_plan_id INTEGER, items TEXT, total INTEGER, direction TEXT, address TEXT, slot TEXT,
  status TEXT DEFAULT 'created', partner TEXT, tracking TEXT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS order_events (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, ts REAL, status TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS ix_orders ON orders(org, status);
"""
# Allowed status flow per direction. delivery = goods to customer; pickup = sample from customer to lab.
FLOW = {
    "delivery": ["created", "confirmed", "packed", "dispatched", "in_transit", "delivered", "cancelled"],
    "pickup": ["created", "confirmed", "scheduled", "collected", "in_transit", "received_at_lab", "cancelled"],
}
KINDS = {"supplement": "delivery", "medicine": "delivery", "retail": "delivery", "device": "delivery", "lab_sample": "pickup", "other": "delivery"}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def create_order(org: str, kind: str, items: list[dict], member_id: int | None = None, patient_id: int | None = None,
                 address: str = "", slot: str | None = None, rx_plan_id: int | None = None, partner: str = "") -> dict:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    direction = KINDS[kind]
    # medicines must reference a signed prescription (safety — never ship Rx without a doctor-signed plan)
    if kind == "medicine":
        if not rx_plan_id:
            raise ValueError("a medicine order needs a signed prescription (rx_plan_id)")
        plan = db.one("SELECT state FROM rx_plans WHERE id = ?", (rx_plan_id,))
        if not plan or plan["state"] not in ("approved", "ordered"):
            raise ValueError("the prescription must be doctor-approved before a medicine order can ship")
    total = sum(int(i.get("price", 0)) * int(i.get("qty", 1)) for i in items)
    now = time.time()
    oid = db.exec_("""INSERT INTO orders (org, kind, member_id, patient_id, rx_plan_id, items, total, direction, address, slot,
                      status, partner, tracking, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (org, kind, member_id, patient_id, rx_plan_id, db.j(items), total, direction, address, slot,
                    "created", partner, None, now, now))
    _event(oid, "created", f"{kind} order, {len(items)} item(s)")
    return order(oid)


def _event(oid: int, status: str, note: str = ""):
    db.exec_("INSERT INTO order_events (order_id, ts, status, note) VALUES (?,?,?,?)", (oid, time.time(), status, note))


def order(oid: int) -> dict | None:
    r = db.one("SELECT * FROM orders WHERE id = ?", (oid,))
    if not r:
        return None
    ev = db.rows("SELECT ts, status, note FROM order_events WHERE order_id = ? ORDER BY ts", (oid,))
    return {**r, "items": db.unj(r["items"], []), "flow": FLOW[r["direction"]], "events": ev}


def advance(oid: int, status: str, note: str = "", tracking: str | None = None) -> dict:
    o = order(oid)
    if not o:
        raise ValueError("no such order")
    flow = FLOW[o["direction"]]
    if status not in flow:
        raise ValueError(f"status must be one of {flow}")
    db.exec_("UPDATE orders SET status = ?, updated_at = ?, tracking = COALESCE(?, tracking) WHERE id = ?",
             (status, time.time(), tracking, oid))
    _event(oid, status, note)
    return order(oid)


def list_orders(org: str, status: str | None = None, kind: str | None = None) -> list[dict]:
    q = "SELECT id FROM orders WHERE org = ?"
    args: list = [org]
    if status:
        q += " AND status = ?"; args.append(status)
    if kind:
        q += " AND kind = ?"; args.append(kind)
    return [order(r["id"]) for r in db.rows(q + " ORDER BY created_at DESC", tuple(args))]


def from_rx_plan(org: str, plan_id: int, address: str = "", slot: str | None = None) -> dict:
    """Turn an approved Rx plan (supplements + medicines) into fulfillment orders — supplements shipped directly,
    medicines via the pharmacy partner against the signed prescription."""
    plan = db.one("SELECT * FROM rx_plans WHERE id = ?", (plan_id,))
    if not plan:
        raise ValueError("no such Rx plan")
    items = db.unj(plan["plan"], {}).get("items", [])
    pid = plan["patient_id"]
    supp = [{"name": i.get("name"), "qty": 1, "price": i.get("price", 0)} for i in items if i.get("kind") in ("formula", "supplement")]
    meds = [{"name": i.get("name"), "qty": 1, "price": i.get("price", 0)} for i in items if i.get("kind") == "medicine"]
    out = []
    if supp:
        out.append(create_order(org, "supplement", supp, patient_id=pid, address=address, slot=slot, rx_plan_id=plan_id))
    if meds:
        out.append(create_order(org, "medicine", meds, patient_id=pid, address=address, slot=slot, rx_plan_id=plan_id))
    return {"created": out}


def schedule_sample_pickup(org: str, patient_id: int, tests: list[str], address: str, slot: str, partner: str = "") -> dict:
    """Book a phlebotomist/courier to collect a blood/urine sample from the customer and take it to the lab."""
    items = [{"name": t, "qty": 1} for t in tests]
    o = create_order(org, "lab_sample", items, patient_id=patient_id, address=address, slot=slot, partner=partner)
    return advance(o["id"], "confirmed", f"pickup booked for {slot}")


def summary(org: str = "default") -> dict:
    rows = db.rows("SELECT kind, status, COUNT(*) AS n FROM orders WHERE org = ? GROUP BY kind, status", (org,))
    active = db.one("SELECT COUNT(*) AS n FROM orders WHERE org = ? AND status NOT IN ('delivered','received_at_lab','cancelled')", (org,))["n"]
    return {"org": org, "active": active, "by_kind_status": rows,
            "note": "Supplements & medicines delivered to the customer; lab samples picked up and taken to the lab."}
