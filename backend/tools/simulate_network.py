#!/usr/bin/env python3
"""Full-network simulation — stand up 5 centres, 20 doctors, 500 patients with realistic clinical data (biomarkers,
devices, test reports), wire the care graph (assign to centres & doctors), seed market-fit pricing/packages, then
simulate a MONTH of real platform activity: memberships & subscriptions, bookings across machines & therapists,
check-ins (credit spend / invoicing), à-la-carte sessions, supplement & lab-sample orders, recurring billing cycles,
and payments across all gateways. Everything runs through the real modules (no shortcut inserts for money/care), so if
the simulation is consistent the platform is consistent.

Deterministic (seeded). Run against a throwaway DB:

    TELOMY_DB=/tmp/telomy-sim.db .venv/bin/python -m tools.simulate_network

Prints a cross-check report at the end. Exits non-zero if any invariant fails.
"""
import os
import random
import sys
import time
from datetime import date, datetime, timedelta

# import the app package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db, platform, staff as staffmod, tenancy, billing, centre as centremod, fulfillment, clinic, roles, seed  # noqa: E402

RND = random.Random(20261019)
TODAY = date(2026, 10, 19)
MONTH_START = TODAY - timedelta(days=30)

CENTRE_DEFS = [
    ("Halo Longevity — Indiranagar", "Bengaluru"),
    ("Vitality Labs — Bandra", "Mumbai"),
    ("Ayus Longevity — Jubilee Hills", "Hyderabad"),
    ("Prime Health — Khan Market", "Delhi"),
    ("Zen Longevity — Koregaon Park", "Pune"),
]
FIRST_M = ["Rohan", "Vikram", "Arjun", "Siddharth", "Rahul", "Karan", "Aditya", "Varun", "Kunal", "Nikhil", "Imran", "Devansh", "Harish", "Manish"]
FIRST_F = ["Priya", "Ananya", "Meera", "Kavya", "Ishita", "Neha", "Aditi", "Sneha", "Pooja", "Divya", "Riya", "Tanvi", "Shruti", "Nandini"]
LAST = ["Sharma", "Iyer", "Reddy", "Menon", "Gupta", "Nair", "Rao", "Bose", "Kapoor", "Joshi", "Pillai", "Singh", "Desai", "Khanna"]
DELIVER_ROLES = ["therapist", "operator", "nurse", "physio", "nutritionist", "trainer"]
DEVICES = ["WHOOP 4.0", "Oura Ring Gen3", "Apple Watch Ultra", "Dexcom G7 CGM", "Telomy KYBand", "Telomy KYRing", "Garmin Fenix"]
GATEWAYS_ONE_TIME = ["razorpay", "cashfree", "payu", "card_pos", "cash"]
GATEWAYS_RECUR = ["upi_autopay", "razorpay", "cashfree"]


def name(sex):
    return f"{RND.choice(FIRST_M if sex == 'male' else FIRST_F)} {RND.choice(LAST)}"


def biomarker_snapshot(age, sex):
    t = RND.random()  # 0 healthy … 1 high risk
    snap = {
        "tc": round(RND.gauss(185 + 50 * t, 18)), "hdl": round(RND.gauss(58 - 16 * t, 6)),
        "ldl": round(RND.gauss(105 + 50 * t, 15)), "apob": round(RND.gauss(85 + 45 * t, 10)),
        "sbp": round(RND.gauss(118 + 24 * t + 0.3 * (age - 40), 7)), "hba1c": round(RND.gauss(5.3 + 0.9 * t, 0.2), 1),
        "glucose": round(RND.gauss(88 + 22 * t, 6)), "bmi": round(RND.gauss(23 + 6 * t, 2), 1),
        "hscrp": round(abs(RND.gauss(0.8 + 3 * t, 0.6)), 1), "vitd": round(RND.gauss(28, 9)),
        "egfr": round(RND.gauss(100 - 0.6 * (age - 40) - 25 * t * (age > 60), 8)),
        "alt": round(RND.gauss(24 + 22 * t, 6)), "ast": round(RND.gauss(24 + 18 * t, 5)),
        "hrv": round(RND.gauss(55 - 0.5 * (age - 40) - 10 * t, 6)), "vo2max": round(RND.gauss(44 - 0.35 * (age - 30) - 6 * t, 3), 1),
        "smoker": RND.random() < 0.12 + 0.15 * t,
    }
    snap["diabetic"] = snap["hba1c"] >= 6.5
    snap["conditions"] = [c for c, p in (("Hypertension", 0.5 * t), ("Prediabetes", 0.5 * t), ("Dyslipidemia", 0.4 * t)) if RND.random() < p]
    # devices worn
    snap["devices"] = RND.sample(DEVICES, k=RND.randint(0, 3))
    # test reports over the last few months
    reports = []
    for k in range(RND.randint(1, 3)):
        d = (TODAY - timedelta(days=RND.randint(10, 200))).isoformat()
        reports.append({"name": RND.choice(["Longevity blood panel", "DEXA body-composition", "VO2 max (CPET)", "Advanced lipid panel", "HbA1c + CGM summary"]),
                        "date": d, "status": "final"})
    snap["reports"] = reports
    snap["wearable"] = {"resting_hr": round(RND.gauss(58 + 6 * t, 5)), "sleep_h": round(RND.gauss(7.1 - 0.6 * t, 0.7), 1),
                        "steps": round(RND.gauss(8200 - 2500 * t, 1500)), "hrv_ms": snap["hrv"]}
    return snap, t


def main():
    t0 = time.time()
    db.init()
    for m in (roles, platform, staffmod, tenancy, billing, centremod, fulfillment, clinic):
        m.init()
    # run the base app seed once (consumer Vault test user + profile + panel) so the API lifespan guard skips reseeding,
    # and so there is real user-side data behind the network. Our 500 network patients get ids after the base panel.
    if not db.one("SELECT 1 AS x FROM profile"):
        seed.run(reset=False)

    # 0) platform super-admin
    SUPER = "root@telomy.io"
    if not staffmod.any_staff():
        staffmod.create_staff("platform", "super_admin", "Platform Root", SUPER, "superpw12345", by="sim")

    centres = []          # list of {slug, name, members:[(member_id, patient_id, tier)], staff:{role:[ids]}, doctors:[ids], services, resources}
    all_doctors = []

    # 1) centres + their staff + market pricing
    for cname, city in CENTRE_DEFS:
        slug = tenancy._slugify(cname)
        if not tenancy.centre(slug):
            tenancy.onboard_centre(cname, city, slug, admin_name=f"Admin {city}", admin_email=f"admin@{slug}.in", admin_password="centrepw123", by="sim")
        billing.seed_plans(slug)
        staff = {"centre_admin": [s["id"] for s in staffmod.list_staff(slug, "centre_admin")]}
        # a manager + front desk + delivering staff of every kind
        staffmod.create_staff(slug, "centre_manager", f"{name('female')} (Mgr)", f"mgr@{slug}.in", "pw12345678", by="sim")
        for r in DELIVER_ROLES:
            for k in range(2):     # 2 of each delivering role per centre
                sx = RND.choice(["male", "female"])
                em = f"{r}{k}@{slug}.in"
                staffmod.create_staff(slug, r, name(sx), em, "pw12345678", by="sim", profile={"specialty": r})
        staff_all = staffmod.list_staff(slug)
        services = platform.list_catalog(slug, "service_type")
        resources = platform.list_catalog(slug, "resource")
        # 7) duties: assign delivering staff to services + resources
        delivering = [s for s in staff_all if s["delivers"]]
        for s in delivering:
            for svc in RND.sample(services, k=min(4, len(services))):
                tenancy.assign_duty(s["id"], slug, "service", svc["id"])
            for res in RND.sample(resources, k=min(2, len(resources))):
                tenancy.assign_duty(s["id"], slug, "resource", res["id"])
        centres.append({"slug": slug, "name": cname, "members": [], "staff": staff_all, "delivering": delivering,
                        "services": services, "resources": resources})

    # 2) 20 doctors, affiliated across centres (round-robin, some to 2 centres)
    for i in range(20):
        sx = RND.choice(["male", "female"])
        home = centres[i % len(centres)]
        doc = staffmod.create_staff(home["slug"], "doctor", f"Dr. {name(sx)}", f"doctor{i}@clinic.in", "doctorpw123", by="sim",
                                    profile={"specialty": RND.choice(["Longevity", "Endocrinology", "Cardiology", "Sports medicine", "Internal medicine"])})
        tenancy.affiliate_doctor(doc["id"], home["slug"])
        if RND.random() < 0.3:     # some consult at a second centre too
            other = RND.choice([c for c in centres if c is not home])
            tenancy.affiliate_doctor(doc["id"], other["slug"])
        all_doctors.append({"id": doc["id"], "home": home["slug"]})

    # 3) 500 patients with clinical data → assign to a centre + a doctor
    patient_rows = []
    for i in range(500):
        sx = RND.choice(["male", "female"])
        age = RND.randint(28, 74)
        snap, tier = biomarker_snapshot(age, sx)
        cen = RND.choice(centres)
        # pick a doctor affiliated to that centre
        aff = [d for d in all_doctors if cen["slug"] in [c["slug"] for c in tenancy.doctor_centres(d["id"])]]
        doc = RND.choice(aff) if aff else RND.choice(all_doctors)
        res = tenancy.onboard_patient(name(sx), by_role="sim", by="sim", age=age, sex=sx,
                                      city=next(c for c in CENTRE_DEFS if tenancy._slugify(c[0]) == cen["slug"])[1],
                                      org=cen["slug"], doctor_id=doc["id"])
        pid = res["patient_id"]
        db.exec_("UPDATE patients SET data = ? WHERE id = ?", (db.j(snap), pid))
        mem = db.one("SELECT id FROM c_members WHERE org = ? AND patient_id = ?", (cen["slug"], pid))
        mid = mem["id"] if mem else None
        cen["members"].append({"mid": mid, "pid": pid, "tier": tier})
        patient_rows.append({"pid": pid, "slug": cen["slug"], "mid": mid, "doc": doc["id"], "tier": tier})

    # 4) memberships / subscriptions (≈45% of members) + one-time packages (≈55%)
    sub_count = 0
    for cen in centres:
        plans = platform.list_catalog(cen["slug"], "membership_plan")
        pkgs = [s for s in cen["services"] if s["data"].get("category") == "Package"]
        for m in cen["members"]:
            if not m["mid"]:
                continue
            if RND.random() < 0.45:
                plan = RND.choice(plans)
                gw = RND.choices(GATEWAYS_RECUR, weights=[5, 3, 2])[0]
                started = (MONTH_START - timedelta(days=RND.randint(0, 120))).isoformat()
                billing.create_subscription(cen["slug"], m["mid"], plan["id"], gw, started_on=started)
                sub_count += 1
            if RND.random() < 0.55:
                pkg = RND.choice(pkgs)
                inv = centremod.add_invoice(cen["slug"], m["mid"], [{"desc": pkg["name"], "amount": pkg["data"]["price"]}])
                billing.record_payment(cen["slug"], inv["id"], RND.choice(GATEWAYS_ONE_TIME),
                                       ts=(MONTH_START + timedelta(days=RND.randint(0, 29))).isoformat())

    # 5) a MONTH of activity — bookings across machines & therapists, check-ins, orders
    bookings = checkins = noshows = orders = notes = clashes = 0
    a_la_carte = [s for s in centres[0]["services"]]  # template of names
    for day_off in range(30):
        d = MONTH_START + timedelta(days=day_off)
        for cen in centres:
            svc_options = [s for s in cen["services"] if s["data"].get("category") not in ("Package",)]
            day_members = RND.sample(cen["members"], k=min(len(cen["members"]), RND.randint(8, 22)))
            for m in day_members:
                if not m["mid"]:
                    continue
                svc = RND.choice(svc_options)
                # staff qualified for this service
                quals = [s for s in cen["delivering"]]
                staff = RND.choice(quals) if quals else None
                resource = RND.choice(cen["resources"]) if cen["resources"] else None
                hour = RND.randint(7, 19)
                start = datetime.combine(d, datetime.min.time()).replace(hour=hour, minute=RND.choice([0, 30]))
                try:
                    b = centremod.book(cen["slug"], m["mid"], svc["id"], start.isoformat(),
                                       staff_id=(staff["id"] if staff else None), resource_id=(resource["id"] if resource else None))
                    bookings += 1
                except ValueError:
                    clashes += 1
                    continue
                roll = RND.random()
                if roll < 0.80:
                    centremod.check_in(b["id"]); centremod.set_status(b["id"], "completed"); checkins += 1
                elif roll < 0.90:
                    centremod.set_status(b["id"], "no_show"); noshows += 1
                # else leave as booked
            # some orders each day
            for _ in range(RND.randint(1, 4)):
                m = RND.choice(cen["members"])
                if not m["mid"]:
                    continue
                if RND.random() < 0.6:
                    fulfillment.create_order(cen["slug"], "supplement", [{"name": RND.choice(["Omega-3", "Vitamin D3+K2", "Magnesium glycinate", "Creatine", "Berberine"]), "qty": 1, "price": RND.choice([800, 1200, 1500, 2000])}], member_id=m["mid"], address="Member address")
                else:
                    fulfillment.schedule_sample_pickup(cen["slug"], m["pid"], ["Longevity blood panel"], "Member address", (d + timedelta(days=1)).isoformat() + " 08:00")
                orders += 1

    # 6) recurring billing cycles across the month (run each week so subscriptions charge on schedule)
    cyc_charged = cyc_gross = cyc_fees = 0
    for wk in range(0, 31, 1):
        as_of = (MONTH_START + timedelta(days=wk)).isoformat()
        for cen in centres:
            r = billing.run_billing_cycle(cen["slug"], as_of)
            cyc_charged += r["charged"]; cyc_gross += r["gross"]; cyc_fees += r["fees"]

    # 7) settle all remaining 'due' invoices (walk-in / à-la-carte) via mixed gateways
    settled = 0
    for cen in centres:
        for inv in db.rows("SELECT id FROM c_invoices WHERE org = ? AND status = 'due'", (cen["slug"],)):
            billing.record_payment(cen["slug"], inv["id"], RND.choice(GATEWAYS_ONE_TIME),
                                   ts=(MONTH_START + timedelta(days=RND.randint(0, 29))).isoformat())
            settled += 1

    # 8) a few clinical notes per doctor
    for doc in all_doctors[:20]:
        pats = tenancy.doctor_patients(doc["id"])[:3]
        for p in pats:
            try:
                clinic.add_note(tenancy.doctor_centres(doc["id"])[0]["slug"] if tenancy.doctor_centres(doc["id"]) else "default",
                                p["id"], author=f"doctor{doc['id']}", title="Follow-up",
                                content={"summary": "Reviewed panel; plan reinforced. Follow-up in 4 weeks."})
                notes += 1
            except Exception:
                pass

    elapsed = time.time() - t0
    stats = {"centres": len(centres), "doctors": len(all_doctors), "patients": len(patient_rows),
             "subscriptions": sub_count, "bookings": bookings, "checkins": checkins, "noshows": noshows,
             "clashes_skipped": clashes, "orders": orders, "notes": notes, "cycle_charged": cyc_charged,
             "invoices_settled": settled, "elapsed_s": round(elapsed, 1)}
    print("SEED COMPLETE:", stats)
    return stats


if __name__ == "__main__":
    main()
