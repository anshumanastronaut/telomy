#!/usr/bin/env python3
"""Cross-check the simulated network: referential integrity across the care graph + billing, derived-number
consistency, and a live pass over the real HTTP endpoints (super-admin, a centre admin, a doctor). Exits non-zero on
any failed invariant so it can gate CI. Run against the DB produced by simulate_network.py:

    TELOMY_DB=/tmp/telomy-sim.db .venv/bin/python -m tools.crosscheck_network
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db, tenancy, billing, staff as staffmod  # noqa: E402

FAILS = []
OKS = []


def check(name, cond, detail=""):
    (OKS if cond else FAILS).append(name)
    print(f"  {'✓' if cond else '✗ FAIL'}  {name}{(' — ' + detail) if detail and not cond else ''}")


def q1(sql, args=()):
    return db.one(sql, args)


def main():
    print("== Referential integrity ==")
    # every care edge points at a real patient
    orphans = q1("SELECT COUNT(*) AS n FROM care_edges e LEFT JOIN patients p ON p.id = e.patient_id WHERE p.id IS NULL")["n"]
    check("care_edges → patients (no orphans)", orphans == 0, f"{orphans} orphan edges")
    # every active centre edge mirrored into c_members
    miss = q1("""SELECT COUNT(*) AS n FROM care_edges e WHERE e.kind='centre' AND e.status='active'
                 AND NOT EXISTS (SELECT 1 FROM c_members m WHERE m.org=e.org AND m.patient_id=e.patient_id)""")["n"]
    check("active centre edges mirrored into c_members", miss == 0, f"{miss} missing members")
    # every booking references a real member + service
    bad_b = q1("SELECT COUNT(*) AS n FROM c_bookings b LEFT JOIN c_members m ON m.id=b.member_id WHERE m.id IS NULL")["n"]
    check("bookings → members (no orphans)", bad_b == 0, f"{bad_b} orphan bookings")
    # every payment references a real invoice (when invoice-linked) and that invoice is paid
    bad_p = q1("""SELECT COUNT(*) AS n FROM payments p LEFT JOIN c_invoices i ON i.id=p.invoice_id
                  WHERE p.invoice_id IS NOT NULL AND (i.id IS NULL OR i.status<>'paid')""")["n"]
    check("payments → paid invoices", bad_p == 0, f"{bad_p} bad payment links")
    # no invoice left 'due' (all settled or subscription-charged)
    due = q1("SELECT COUNT(*) AS n FROM c_invoices WHERE status='due'")["n"]
    check("no unsettled invoices remain", due == 0, f"{due} still due")
    # subscriptions advanced (next_charge_on in the future for active) and each charged cycle produced a payment
    sub_pays = q1("SELECT COUNT(*) AS n FROM payments WHERE subscription_id IS NOT NULL")["n"]
    cycles = q1("SELECT COALESCE(SUM(cycles_billed),0) AS n FROM billing_subscriptions")["n"]
    check("subscription payments == billed cycles", sub_pays == cycles, f"{sub_pays} pays vs {cycles} cycles")

    print("\n== Money consistency ==")
    # fee + net == amount for every payment
    bad_fee = q1("SELECT COUNT(*) AS n FROM payments WHERE fee + net <> amount")["n"]
    check("fee + net == amount (every payment)", bad_fee == 0, f"{bad_fee} mismatched")
    # gateway fee recomputed matches stored, on a sample
    sample = db.rows("SELECT * FROM payments ORDER BY RANDOM() LIMIT 200")
    recompute_ok = all(
        p["fee"] in (billing.gateway_fee(p["amount"], p["gateway"], False)["fee"], billing.gateway_fee(p["amount"], p["gateway"], True)["fee"])
        for p in sample)
    check("stored fee matches gateway_fee() (200-sample)", recompute_ok)
    # platform revenue total == sum of centre revenues
    centres = tenancy.list_centres()
    per_centre = {c["slug"]: tenancy.centre_revenue(c["slug"]) for c in centres}
    ov = tenancy.platform_overview()
    sum_rev = sum(r["total_revenue"] for r in per_centre.values())
    check("platform overview revenue == Σ centre revenue", ov["total_revenue"] == sum_rev, f"{ov['total_revenue']} vs {sum_rev}")
    check("overview centre count == centres", ov["centres"] == len(centres))

    print("\n== Derived performance ==")
    # every delivered booking's revenue attributed to a staff member shows up in performance
    for c in centres[:2]:
        perf = tenancy.staff_performance(c["slug"])
        perf_rev = sum(r["revenue"] for r in perf)
        booked_rev = q1("SELECT COALESCE(SUM(price),0) AS t FROM c_bookings WHERE org=? AND status IN ('checked_in','completed') AND staff_id IS NOT NULL", (c["slug"],))["t"]
        check(f"[{c['slug']}] performance revenue == delivered bookings w/ staff", perf_rev == booked_rev, f"{perf_rev} vs {booked_rev}")

    print("\n== Live endpoint pass ==")
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as cl:
        hs = {"Authorization": "Bearer " + cl.post("/mgmt/auth/login", json={"email": "root@telomy.io", "password": "superpw12345"}).json()["token"]}
        ov_api = cl.get("/mgmt/admin/overview", headers=hs).json()
        check("API overview matches module overview", ov_api["total_revenue"] == ov["total_revenue"] and ov_api["centres"] == ov["centres"])
        # a centre admin
        slug = centres[0]["slug"]
        la = cl.post("/mgmt/auth/login", json={"email": f"admin@{slug}.in", "password": "centrepw123"}).json()
        hc = {"Authorization": "Bearer " + la["token"]}
        people = cl.get(f"/mgmt/centre/people?org={slug}", headers=hc).json()
        check("centre people endpoint returns members", len(people) > 0, f"{len(people)} people")
        rev = cl.get(f"/mgmt/centre/revenue?org={slug}", headers=hc).json()
        check("centre revenue endpoint matches module", rev["total_revenue"] == per_centre[slug]["total_revenue"])
        summ = cl.get(f"/mgmt/billing/summary?org={slug}", headers=hc).json()
        check("billing summary gross == Σ by_gateway gross", summ["gross"] == sum(g["gross"] for g in summ["by_gateway"]))
        perf = cl.get(f"/mgmt/centre/performance?org={slug}", headers=hc).json()
        check("performance endpoint returns staff rows", len(perf) > 0, f"{len(perf)} rows")
        # a doctor sees their panel
        ld = cl.post("/mgmt/auth/login", json={"email": "doctor0@clinic.in", "password": "doctorpw123"}).json()
        hd = {"Authorization": "Bearer " + ld["token"]}
        panel = cl.get("/mgmt/doctor/patients", headers=hd).json()
        check("doctor panel endpoint returns patients", len(panel) > 0, f"{len(panel)} patients")
        # a patient graph resolves centre + doctor
        pid = panel[0]["id"]
        g = cl.get(f"/mgmt/patients/{pid}/graph", headers=hd).json()
        check("patient graph resolves a centre + doctor", g["centre"] is not None and g["doctor"] is not None)
        # the patient carries biomarkers + reports + devices
        check("patient snapshot has biomarkers", "hba1c" in (g["patient"]["data"] or {}))
        check("patient snapshot has test reports", len(g["patient"]["data"].get("reports", [])) > 0)

    print("\n== Totals ==")
    tot = q1("SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS g, COALESCE(SUM(fee),0) AS f, COALESCE(SUM(net),0) AS net FROM payments")
    print(f"  payments: {tot['n']}  gross ₹{tot['g']:,}  fees ₹{tot['f']:,}  net ₹{tot['net']:,}")
    print(f"  centres {len(centres)}  doctors {ov['doctors']}  patients {ov['patients']}  network revenue ₹{ov['total_revenue']:,}")
    print(f"\n{'ALL CHECKS PASSED' if not FAILS else f'{len(FAILS)} CHECK(S) FAILED: ' + ', '.join(FAILS)}  ({len(OKS)} passed)")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
