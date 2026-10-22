"""Billing, payments & subscriptions — the money layer, so a centre runs everything (pricing, packages, memberships,
gateways, reconciliation) from one app with no separate billing tool.

Market: India longevity / wellness-centre segment (2025-26). Figures are grounded in published commentary — see
docs/research/PRICING_PAYMENTS_INDIA.md. Memberships are recurring (UPI AutoPay / card e-mandate); assessment packages
are one-time; therapies/diagnostics are à-la-carte and already modelled as services (platform catalog).

Gateways carry a realistic MDR (merchant discount rate) so fees and net settlement are computed, not guessed:
  razorpay  ~2.0% (+0.99% on subscriptions),  cashfree ~1.95%,  payu ~2.0%,  upi_autopay 0% (UPI MDR nil),
  card_pos ~2.0%,  cash 0%.  GST 18% applies on the MDR fee.

This module sits on top of centre.py invoices: a payment settles an invoice (or a subscription cycle), records the
gateway/fee/net, and reconciles. It never deletes financial records.
"""
import time
from datetime import date, datetime, timedelta

from . import db, platform

SCHEMA = """
CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, member_id INTEGER, invoice_id INTEGER,
  subscription_id INTEGER, gateway TEXT, method TEXT, amount INTEGER, fee INTEGER, net INTEGER, status TEXT DEFAULT 'captured',
  ref TEXT, ts TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_payments ON payments(org, ts);
CREATE TABLE IF NOT EXISTS billing_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, member_id INTEGER, plan_id INTEGER,
  plan_name TEXT, amount INTEGER, cycle_days INTEGER, gateway TEXT, mandate_ref TEXT, status TEXT DEFAULT 'active',
  started_on TEXT, next_charge_on TEXT, cycles_billed INTEGER DEFAULT 0, data TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_subs ON billing_subscriptions(org, status, next_charge_on);
"""

# MDR per gateway: (base rate one-time, extra rate when recurring). GST charged on the fee.
GATEWAYS = {
    "razorpay": {"base": 0.0200, "recurring_add": 0.0099, "label": "Razorpay", "settlement": "T+2", "supports_mandate": True},
    "cashfree": {"base": 0.0195, "recurring_add": 0.0000, "label": "Cashfree", "settlement": "T+1", "supports_mandate": True},
    "payu": {"base": 0.0200, "recurring_add": 0.0000, "label": "PayU", "settlement": "T+2", "supports_mandate": True},
    "upi_autopay": {"base": 0.0000, "recurring_add": 0.0000, "label": "UPI AutoPay", "settlement": "T+1", "supports_mandate": True},
    "card_pos": {"base": 0.0200, "recurring_add": 0.0000, "label": "Card (POS)", "settlement": "T+2", "supports_mandate": False},
    "cash": {"base": 0.0000, "recurring_add": 0.0000, "label": "Cash", "settlement": "instant", "supports_mandate": False},
}
GST = 0.18

# --- Market-researched plan catalog (INR). Seeded per centre so enroll()/booking() work against real items. ---
MEMBERSHIP_PLANS = [
    {"name": "Core Longevity (Monthly)", "price": 12999, "cycle_days": 30, "credits": 4,
     "entitlements": ["Quarterly 90+ biomarker panel", "2 physician consults / mo", "4 therapy credits / mo", "Dietitian access"]},
    {"name": "Core Longevity (Annual)", "price": 129999, "cycle_days": 365, "credits": 48,
     "entitlements": ["Everything in Core", "~2 months free vs monthly", "Annual DEXA + VO2"]},
    {"name": "Plus Longevity (Monthly)", "price": 24999, "cycle_days": 30, "credits": 8,
     "entitlements": ["Monthly consults", "8 therapy credits / mo", "1 IV drip / mo", "Quarterly DEXA", "130+ biomarker panel / quarter"]},
    {"name": "Elite Longevity (Monthly)", "price": 99999, "cycle_days": 30, "credits": None,
     "entitlements": ["Dedicated physician", "Unlimited consults & therapies", "Monthly full panel + imaging", "Priority scheduling"]},
]
# One-time assessment packages — modelled as service_type so they book & bill through the normal flow.
PACKAGES = [
    {"name": "Essential Health Check", "price": 4999, "minutes": 60, "category": "Package", "desc": "Core blood panel + vitals + body comp"},
    {"name": "Longevity Assessment", "price": 24999, "minutes": 180, "category": "Package", "desc": "90+ biomarkers, DEXA, VO2 max, consult"},
    {"name": "Comprehensive Longevity Panel", "price": 49999, "minutes": 240, "category": "Package", "desc": "130+ biomarkers, advanced imaging, two consults"},
    {"name": "Executive 360", "price": 89999, "minutes": 300, "category": "Package", "desc": "Full longevity work-up, cardiac CT, full-body MRI screen"},
]
# À-la-carte therapies / diagnostics (ids are keys; prices in INR).
SERVICES = [
    {"name": "Infrared sauna", "price": 900, "minutes": 30, "category": "Recovery"},
    {"name": "Cold plunge", "price": 600, "minutes": 10, "category": "Recovery"},
    {"name": "Hyperbaric oxygen (HBOT)", "price": 4500, "minutes": 60, "category": "Therapy"},
    {"name": "IV micronutrient drip", "price": 3500, "minutes": 45, "category": "Therapy"},
    {"name": "Red-light therapy", "price": 800, "minutes": 20, "category": "Recovery"},
    {"name": "DEXA body-composition scan", "price": 3500, "minutes": 20, "category": "Diagnostics"},
    {"name": "VO2 max test (CPET)", "price": 6000, "minutes": 45, "category": "Diagnostics"},
    {"name": "Longevity blood panel", "price": 5500, "minutes": 15, "category": "Diagnostics"},
    {"name": "Doctor consultation", "price": 1500, "minutes": 30, "category": "Consultation"},
    {"name": "Strength coaching session", "price": 1800, "minutes": 60, "category": "Training"},
]
RESOURCES = ["Sauna room", "Cold plunge", "HBOT chamber", "IV lounge chair", "Red-light room", "DEXA suite",
             "CPET lab", "Phlebotomy room", "Consult room A", "Gym floor"]


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ---- gateways & fees --------------------------------------------------------------------------------------------

def gateway_fee(amount: int, gateway: str, recurring: bool = False) -> dict:
    g = GATEWAYS.get(gateway)
    if not g:
        raise ValueError(f"unknown gateway {gateway}")
    rate = g["base"] + (g["recurring_add"] if recurring else 0.0)
    fee = round(amount * rate * (1 + GST))
    return {"rate": rate, "fee": fee, "net": amount - fee}


def gateways() -> list[dict]:
    return [{"key": k, **v} for k, v in GATEWAYS.items()]


# ---- plan seeding (into the platform catalog, so the rest of the system uses them unchanged) ---------------------

def seed_plans(org: str) -> dict:
    """Seed this centre's catalog with market-fit memberships, packages, therapies and resources (idempotent-ish:
    only seeds kinds that are currently empty)."""
    out = {"memberships": 0, "packages": 0, "services": 0, "resources": 0}
    if not platform.list_catalog(org, "membership_plan"):
        for p in MEMBERSHIP_PLANS:
            platform.add_catalog(org, "membership_plan", p["name"],
                                 {"price": p["price"], "cycle_days": p["cycle_days"], "credits": p["credits"], "entitlements": p["entitlements"]})
            out["memberships"] += 1
    existing_svc = {s["name"] for s in platform.list_catalog(org, "service_type")}
    for p in PACKAGES:
        if p["name"] not in existing_svc:
            platform.add_catalog(org, "service_type", p["name"], {"price": p["price"], "minutes": p["minutes"], "category": p["category"], "desc": p["desc"]})
            out["packages"] += 1
    for s in SERVICES:
        if s["name"] not in existing_svc:
            platform.add_catalog(org, "service_type", s["name"], {"price": s["price"], "minutes": s["minutes"], "category": s["category"]})
            out["services"] += 1
    if not platform.list_catalog(org, "resource"):
        for r in RESOURCES:
            platform.add_catalog(org, "resource", r, {})
            out["resources"] += 1
    return out


# ---- payments ---------------------------------------------------------------------------------------------------

def record_payment(org: str, invoice_id: int | None, gateway: str, *, member_id: int | None = None,
                   amount: int | None = None, subscription_id: int | None = None, recurring: bool = False,
                   ref: str | None = None, ts: str | None = None) -> dict:
    """Capture a payment against an invoice (or a subscription cycle), compute gateway fee/net, and settle the invoice."""
    from . import centre as centremod
    if invoice_id is not None:
        inv = centremod.invoice(invoice_id)
        if not inv:
            raise ValueError("no such invoice")
        amount = inv["total"]
        member_id = inv["member_id"]
    if amount is None:
        raise ValueError("amount or invoice_id required")
    fee = gateway_fee(amount, gateway, recurring)
    ts = ts or datetime.now().isoformat()
    pid = db.exec_("""INSERT INTO payments (org, member_id, invoice_id, subscription_id, gateway, method, amount, fee, net,
                      status, ref, ts, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (org, member_id, invoice_id, subscription_id, gateway, gateway, amount, fee["fee"], fee["net"],
                    "captured", ref or f"{gateway[:3].upper()}-{int(time.time()*1000)%10**8}", ts, time.time()))
    if invoice_id is not None:
        db.exec_("UPDATE c_invoices SET status = 'paid', method = ? WHERE id = ?", (gateway, invoice_id))
    return payment(pid)


def payment(pid: int) -> dict | None:
    return db.one("SELECT * FROM payments WHERE id = ?", (pid,))


def list_payments(org: str, since: str | None = None, limit: int = 500) -> list[dict]:
    q = "SELECT * FROM payments WHERE org = ?"
    args: list = [org]
    if since:
        q += " AND ts >= ?"; args.append(since)
    return db.rows(q + " ORDER BY ts DESC LIMIT ?", tuple(args + [limit]))


# ---- subscriptions (recurring memberships) ----------------------------------------------------------------------

def create_subscription(org: str, member_id: int, plan_id: int, gateway: str, started_on: str | None = None) -> dict:
    plan = platform.catalog_item(plan_id)
    if not plan or plan["kind"] != "membership_plan":
        raise ValueError("no such membership plan")
    g = GATEWAYS.get(gateway)
    if not g or not g["supports_mandate"]:
        raise ValueError("that gateway cannot hold a recurring mandate")
    d = plan["data"]
    start = started_on or date.today().isoformat()
    cycle = int(d.get("cycle_days", 30))
    sid = db.exec_("""INSERT INTO billing_subscriptions (org, member_id, plan_id, plan_name, amount, cycle_days, gateway, mandate_ref,
                      status, started_on, next_charge_on, cycles_billed, data, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?)""",
                   (org, member_id, plan_id, plan["name"], int(d.get("price", 0)), cycle, gateway,
                    f"MND-{int(time.time()*1000)%10**8}", "active", start, start, db.j({"entitlements": d.get("entitlements", [])}), time.time()))
    return subscription(sid)


def subscription(sid: int) -> dict | None:
    r = db.one("SELECT * FROM billing_subscriptions WHERE id = ?", (sid,))
    return {**r, "data": db.unj(r["data"], {})} if r else None


def run_billing_cycle(org: str, as_of: str) -> dict:
    """Charge every subscription whose next_charge_on <= as_of: raise an invoice, capture the payment on the mandate's
    gateway (recurring MDR), advance the schedule. Returns how many charged and the gross/fees."""
    from . import centre as centremod
    due = db.rows("SELECT * FROM billing_subscriptions WHERE org = ? AND status = 'active' AND next_charge_on <= ?", (org, as_of))
    charged = 0; gross = 0; fees = 0
    for s in due:
        inv = centremod.add_invoice(org, s["member_id"], [{"desc": f"Subscription — {s['plan_name']}", "amount": s["amount"]}])
        pay = record_payment(org, inv["id"], s["gateway"], subscription_id=s["id"], recurring=True,
                             ts=datetime.fromisoformat(s["next_charge_on"] + "T09:00:00").isoformat() if len(s["next_charge_on"]) == 10 else s["next_charge_on"])
        nxt = (date.fromisoformat(s["next_charge_on"]) + timedelta(days=s["cycle_days"])).isoformat()
        db.exec_("UPDATE billing_subscriptions SET next_charge_on = ?, cycles_billed = cycles_billed + 1 WHERE id = ?", (nxt, s["id"]))
        charged += 1; gross += pay["amount"]; fees += pay["fee"]
    return {"org": org, "as_of": as_of, "charged": charged, "gross": gross, "fees": fees, "net": gross - fees}


# ---- reconciliation ---------------------------------------------------------------------------------------------

def summary(org: str, since: str | None = None) -> dict:
    where = "org = ?"
    args: list = [org]
    if since:
        where += " AND ts >= ?"; args.append(since)
    by_gw = db.rows(f"SELECT gateway, COUNT(*) AS n, COALESCE(SUM(amount),0) AS gross, COALESCE(SUM(fee),0) AS fees, COALESCE(SUM(net),0) AS net FROM payments WHERE {where} GROUP BY gateway ORDER BY gross DESC", tuple(args))
    tot = db.one(f"SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS gross, COALESCE(SUM(fee),0) AS fees, COALESCE(SUM(net),0) AS net FROM payments WHERE {where}", tuple(args))
    subs = db.one("SELECT COUNT(*) AS n FROM billing_subscriptions WHERE org = ? AND status = 'active'", (org,))
    mrr = db.one("SELECT COALESCE(SUM(CASE WHEN cycle_days<=31 THEN amount ELSE amount*30.0/cycle_days END),0) AS mrr FROM billing_subscriptions WHERE org = ? AND status='active'", (org,))
    return {"org": org, "payments": tot["n"], "gross": tot["gross"], "fees": tot["fees"], "net": tot["net"],
            "active_subscriptions": subs["n"], "mrr": round(mrr["mrr"]), "by_gateway": by_gw}
