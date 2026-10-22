"""Billing: market-fit plans seed, gateway fees (incl. GST + recurring add), invoice payment, subscriptions and the
recurring billing cycle, and reconciliation."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "billing.db"))
import pytest  # noqa: E402
from app import db, platform, centre as centremod, billing  # noqa: E402

ORG = "bill-test"


@pytest.fixture(scope="module", autouse=True)
def setup():
    db.init()
    for m in (platform, centremod, billing):
        m.init()
    billing.seed_plans(ORG)
    yield


def test_seed_plans_present():
    plans = platform.list_catalog(ORG, "membership_plan")
    assert any("Elite" in p["name"] for p in plans)
    pkgs = [s for s in platform.list_catalog(ORG, "service_type") if s["data"].get("category") == "Package"]
    assert any("Longevity Assessment" in p["name"] for p in pkgs)


def test_gateway_fee_gst_and_recurring():
    # razorpay one-time: 2% * 1.18 GST on ₹10,000 = ₹236
    f = billing.gateway_fee(10000, "razorpay", recurring=False)
    assert f["fee"] == round(10000 * 0.02 * 1.18) == 236 and f["net"] == 10000 - 236
    # recurring adds 0.99%
    fr = billing.gateway_fee(10000, "razorpay", recurring=True)
    assert fr["fee"] == round(10000 * 0.0299 * 1.18)
    # UPI AutoPay is nil MDR
    assert billing.gateway_fee(10000, "upi_autopay", recurring=True)["fee"] == 0
    with pytest.raises(ValueError):
        billing.gateway_fee(100, "nope")


def test_invoice_payment_settles_and_reconciles():
    m = centremod.add_member(ORG, "Pay Test")
    inv = centremod.add_invoice(ORG, m["id"], [{"desc": "Longevity Assessment", "amount": 24999}])
    assert inv["status"] == "due"
    pay = billing.record_payment(ORG, inv["id"], "cashfree")
    assert pay["amount"] == 24999 and pay["fee"] + pay["net"] == 24999
    assert centremod.invoice(inv["id"])["status"] == "paid"
    s = billing.summary(ORG)
    assert s["gross"] >= 24999 and s["gross"] == sum(g["gross"] for g in s["by_gateway"])


def test_subscription_cycle_charges_once_per_cycle():
    m = centremod.add_member(ORG, "Sub Test")
    plan = next(p for p in platform.list_catalog(ORG, "membership_plan") if p["data"]["cycle_days"] == 30)
    sub = billing.create_subscription(ORG, m["id"], plan["id"], "upi_autopay", started_on="2026-01-01")
    assert sub["next_charge_on"] == "2026-01-01"
    # a cycle run on 2026-01-05 charges the Jan-01 due date once
    r1 = billing.run_billing_cycle(ORG, "2026-01-05")
    assert r1["charged"] == 1 and r1["gross"] == plan["data"]["price"]
    # running again same day does NOT double charge (next_charge_on advanced to Feb-01)
    r2 = billing.run_billing_cycle(ORG, "2026-01-05")
    assert r2["charged"] == 0
    # a run after the next due date charges the second cycle
    r3 = billing.run_billing_cycle(ORG, "2026-02-02")
    assert r3["charged"] == 1
    sub2 = billing.subscription(sub["id"])
    assert sub2["cycles_billed"] == 2
    # a card gateway cannot hold a recurring mandate
    with pytest.raises(ValueError):
        billing.create_subscription(ORG, m["id"], plan["id"], "card_pos")
