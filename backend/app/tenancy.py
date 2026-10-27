"""Tenancy & the care graph — the backbone that ties the four workspaces together (super-admin / doctor / centre /
user) with one coherent, auditable model. Everything is a relationship in a small set of tables, so the whole network
can be reasoned about and rolled up without duplicating state across modules.

Entities & edges
  * centres            — a wellness centre == an `org` (its slug is the org key used everywhere else: platform.py config,
                         centre.py ops, fulfillment.py, staff.py). The super-admin onboards centres.
  * staff (staff.py)   — every operator of any workspace. Scoped to an org (centres) or to the platform (super-admin).
  * provider_centre    — doctor ⇄ centre affiliation (M:N). A doctor may consult at several centres; a centre lists its
                         affiliated doctors. Independent doctors simply have none.
  * patients (roles.py)— the person being cared for (seed panel or a real app user, linked by `user_ref`).
  * care_edges         — the assignment graph: patient → centre and patient → doctor, with who assigned it and when.
                         A doctor intakes a patient and assigns them to a centre; a centre onboards a user and assigns
                         them to a doctor. Both write the same edge table, so either side sees the full picture.
  * staff_duties       — operational staff (therapist / operator / nurse / physio / trainer) ⇄ the therapy (service_type)
                         or machine (resource) they are qualified to run. Drives scheduling and performance attribution.

Rollups (no separate stores — always derived, so numbers can never drift):
  * staff performance  — sessions delivered + revenue, from c_bookings.staff_id × price (centre.py).
  * centre revenue     — paid invoices + delivered-booking value + fulfilled orders.
  * platform overview  — counts and revenue across every centre (super-admin).

Safety: this module never deletes a person's clinical data; de-assigning only closes an edge (status='ended').
"""
import time
from datetime import date, datetime

from . import db, platform, staff as staffmod

SCHEMA = """
CREATE TABLE IF NOT EXISTS centres (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, name TEXT, city TEXT,
  status TEXT DEFAULT 'active', data TEXT, created_by TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS provider_centre (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_id INTEGER, org TEXT,
  status TEXT DEFAULT 'active', created_at REAL, UNIQUE(doctor_id, org));
CREATE TABLE IF NOT EXISTS care_edges (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, user_ref TEXT,
  kind TEXT, org TEXT, doctor_id INTEGER, status TEXT DEFAULT 'active', assigned_by TEXT, note TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_care_edges ON care_edges(patient_id, kind, status);
CREATE INDEX IF NOT EXISTS ix_care_edges_org ON care_edges(org, kind, status);
CREATE TABLE IF NOT EXISTS staff_duties (id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id INTEGER, org TEXT,
  duty_kind TEXT, ref_id INTEGER, created_at REAL, UNIQUE(staff_id, duty_kind, ref_id));
"""
# care_edges.kind: 'centre' (patient↔org) | 'doctor' (patient↔doctor). staff_duties.duty_kind: 'service' | 'resource'.


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ---- centres (orgs) ---------------------------------------------------------------------------------------------

def _slugify(name: str) -> str:
    s = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s[:40] or "centre"


def onboard_centre(name: str, city: str = "", slug: str | None = None, admin_name: str = "", admin_email: str = "",
                   admin_password: str = "", by: str = "super_admin", branding: dict | None = None) -> dict:
    """Super-admin: create a centre (org), seed its default config, and (optionally) its first centre-admin login."""
    init()
    slug = _slugify(slug or name)
    base, n = slug, 2
    while db.one("SELECT 1 AS x FROM centres WHERE slug = ?", (slug,)):
        slug = f"{base}-{n}"; n += 1
    cid = db.exec_("INSERT INTO centres (slug, name, city, status, data, created_by, created_at) VALUES (?,?,?,?,?,?,?)",
                   (slug, name.strip(), city.strip(), "active", db.j({}), by, time.time()))
    # seed org config so the centre's console works immediately
    platform.set_org(slug, kind="centre", branding={"name": name.strip(), **(branding or {})})
    admin = None
    if admin_email and admin_password:
        admin = staffmod.create_staff(slug, "centre_admin", admin_name or name, admin_email, admin_password, by=by)
    return {"id": cid, "slug": slug, "name": name.strip(), "city": city, "admin": admin}


def centre(slug: str) -> dict | None:
    r = db.one("SELECT * FROM centres WHERE slug = ?", (slug,))
    if not r:
        return None
    return {**r, "data": db.unj(r["data"], {})}


def list_centres() -> list[dict]:
    init()
    return [{**r, "data": db.unj(r["data"], {})} for r in db.rows("SELECT * FROM centres ORDER BY name")]


def set_centre_status(slug: str, status: str):
    db.exec_("UPDATE centres SET status = ? WHERE slug = ?", (status, slug))


# ---- doctor ⇄ centre affiliation --------------------------------------------------------------------------------

def affiliate_doctor(doctor_id: int, org: str) -> dict:
    init()
    doc = staffmod.get_staff(doctor_id)
    if not doc or doc["workspace"] != "doctor":
        raise ValueError("doctor_id must be a doctor-side staff account")
    db.exec_("INSERT OR IGNORE INTO provider_centre (doctor_id, org, status, created_at) VALUES (?,?,?,?)",
             (doctor_id, org, "active", time.time()))
    db.exec_("UPDATE provider_centre SET status = 'active' WHERE doctor_id = ? AND org = ?", (doctor_id, org))
    return {"doctor_id": doctor_id, "org": org, "status": "active"}


def centre_doctors(org: str) -> list[dict]:
    rows = db.rows("SELECT doctor_id FROM provider_centre WHERE org = ? AND status = 'active'", (org,))
    return [d for d in (staffmod.get_staff(r["doctor_id"]) for r in rows) if d]


def doctor_centres(doctor_id: int) -> list[dict]:
    rows = db.rows("SELECT org FROM provider_centre WHERE doctor_id = ? AND status = 'active'", (doctor_id,))
    return [centre(r["org"]) for r in rows if centre(r["org"])]


# ---- the care graph: patient ⇄ centre / doctor ------------------------------------------------------------------

def _ensure_patient(name: str, user_ref: str | None = None, age: float | None = None, sex: str | None = None,
                    city: str = "", doctor_id: int | None = None) -> int:
    """Find-or-create the person in the clinical panel (roles.py `patients`)."""
    if user_ref:
        ex = db.one("SELECT id FROM patients WHERE json_extract(data,'$.user_ref') = ?", (user_ref,))
        if ex:
            return ex["id"]
    pid = db.exec_("INSERT INTO patients (name, age, sex, city, doctor_id, member, plan, data, joined) VALUES (?,?,?,?,?,?,?,?,?)",
                   (name.strip(), age, sex, city, doctor_id, 0, None, db.j({"user_ref": user_ref} if user_ref else {}),
                    date.today().isoformat()))
    return pid


def onboard_patient(name: str, by_role: str, by: str = "", user_ref: str | None = None, age: float | None = None,
                    sex: str | None = None, city: str = "", org: str | None = None, doctor_id: int | None = None) -> dict:
    """Doctor or centre onboards a person, then (optionally) assigns them to a centre and/or a doctor in one step."""
    init()
    pid = _ensure_patient(name, user_ref=user_ref, age=age, sex=sex, city=city, doctor_id=doctor_id)
    edges = []
    if org:
        edges.append(assign_to_centre(pid, org, by=by or by_role))
    if doctor_id:
        edges.append(assign_to_doctor(pid, doctor_id, by=by or by_role))
    return {"patient_id": pid, "name": name, "edges": edges}


def _open_edge(patient_id: int, kind: str, *, org: str | None = None, doctor_id: int | None = None,
               by: str = "", note: str = "") -> dict:
    # close any existing open edge of this kind for the patient (a patient has one active centre / one active doctor)
    db.exec_("UPDATE care_edges SET status = 'ended' WHERE patient_id = ? AND kind = ? AND status = 'active'",
             (patient_id, kind))
    eid = db.exec_("""INSERT INTO care_edges (patient_id, user_ref, kind, org, doctor_id, status, assigned_by, note, created_at)
                      VALUES (?,?,?,?,?,?,?,?,?)""",
                   (patient_id, None, kind, org, doctor_id, "active", by, note, time.time()))
    return {"id": eid, "patient_id": patient_id, "kind": kind, "org": org, "doctor_id": doctor_id, "by": by}


def assign_to_centre(patient_id: int, org: str, by: str = "", note: str = "") -> dict:
    init()
    if not centre(org):
        raise ValueError("no such centre")
    e = _open_edge(patient_id, "centre", org=org, by=by, note=note)
    # mirror into the centre's member list so centre.py screens see them
    p = db.one("SELECT name, data FROM patients WHERE id = ?", (patient_id,))
    if p and not db.one("SELECT 1 AS x FROM c_members WHERE org = ? AND patient_id = ?", (org, patient_id)):
        from . import centre as centremod
        centremod.add_member(org, p["name"], patient_id=patient_id)
    return e


def assign_to_doctor(patient_id: int, doctor_id: int, by: str = "", note: str = "") -> dict:
    init()
    doc = staffmod.get_staff(doctor_id)
    if not doc or doc["workspace"] != "doctor":
        raise ValueError("doctor_id must be a doctor-side staff account")
    db.exec_("UPDATE patients SET doctor_id = ? WHERE id = ?", (doctor_id, patient_id))
    return _open_edge(patient_id, "doctor", doctor_id=doctor_id, by=by, note=note)


def end_edge(edge_id: int):
    db.exec_("UPDATE care_edges SET status = 'ended' WHERE id = ?", (edge_id,))


def patient_graph(patient_id: int) -> dict:
    """Everything connected to a person — their centre, doctor, and history. Used so no view loses the thread."""
    p = db.one("SELECT * FROM patients WHERE id = ?", (patient_id,))
    edges = db.rows("SELECT * FROM care_edges WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))
    cen = next((e for e in edges if e["kind"] == "centre" and e["status"] == "active"), None)
    doc = next((e for e in edges if e["kind"] == "doctor" and e["status"] == "active"), None)
    return {"patient": ({**p, "data": db.unj(p["data"], {})} if p else None),
            "centre": (centre(cen["org"]) if cen else None),
            "doctor": (staffmod.get_staff(doc["doctor_id"]) if doc else None),
            "history": edges}


def centre_patients(org: str) -> list[dict]:
    rows = db.rows("SELECT DISTINCT patient_id FROM care_edges WHERE org = ? AND kind = 'centre' AND status = 'active'", (org,))
    out = []
    for r in rows:
        p = db.one("SELECT id, name, age, sex, city, doctor_id FROM patients WHERE id = ?", (r["patient_id"],))
        if p:
            out.append({**p, "doctor": (staffmod.get_staff(p["doctor_id"]) or {}).get("name") if p["doctor_id"] else None})
    return out


def doctor_patients(doctor_id: int) -> list[dict]:
    rows = db.rows("SELECT id, name, age, sex, city FROM patients WHERE doctor_id = ? ORDER BY name", (doctor_id,))
    return [dict(r) for r in rows]


# ---- operational staff ⇄ therapy / machine ----------------------------------------------------------------------

def assign_duty(staff_id: int, org: str, duty_kind: str, ref_id: int) -> dict:
    if duty_kind not in ("service", "resource"):
        raise ValueError("duty_kind must be 'service' or 'resource'")
    init()
    db.exec_("INSERT OR IGNORE INTO staff_duties (staff_id, org, duty_kind, ref_id, created_at) VALUES (?,?,?,?,?)",
             (staff_id, org, duty_kind, ref_id, time.time()))
    return {"staff_id": staff_id, "duty_kind": duty_kind, "ref_id": ref_id}


def remove_duty(staff_id: int, duty_kind: str, ref_id: int):
    db.exec_("DELETE FROM staff_duties WHERE staff_id = ? AND duty_kind = ? AND ref_id = ?", (staff_id, duty_kind, ref_id))


def staff_duties(org: str, staff_id: int | None = None) -> list[dict]:
    q = "SELECT * FROM staff_duties WHERE org = ?"
    args: list = [org]
    if staff_id:
        q += " AND staff_id = ?"; args.append(staff_id)
    out = []
    for r in db.rows(q, tuple(args)):
        item = db.one("SELECT name FROM catalog WHERE id = ?", (r["ref_id"],))
        out.append({**r, "name": item["name"] if item else f"#{r['ref_id']}"})
    return out


# ---- performance & revenue (always derived) ---------------------------------------------------------------------

_DELIVERED = ("checked_in", "completed")


def staff_performance(org: str, staff_id: int | None = None, since: str | None = None) -> list[dict]:
    """Sessions delivered and revenue earned per operational staff member, from the booking ledger."""
    out = []
    staff_list = [staffmod.get_staff(staff_id)] if staff_id else staffmod.list_staff(org)
    for s in staff_list:
        if not s:
            continue
        sid = s["id"]
        where = "org = ? AND staff_id = ?"
        args: list = [org, sid]
        if since:
            where += " AND start_ts >= ?"; args.append(since)
        booked = db.one(f"SELECT COUNT(*) AS n FROM c_bookings WHERE {where}", tuple(args))["n"]
        done = db.one(f"SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS rev FROM c_bookings WHERE {where} AND status IN {_DELIVERED}", tuple(args))
        out.append({"staff_id": sid, "name": s["name"], "role": s["role"], "label": s.get("label"),
                    "delivers": s.get("delivers", False), "booked": booked, "delivered": done["n"],
                    "revenue": done["rev"], "no_show": max(0, booked - done["n"])})
    # operational staff first, by revenue
    out.sort(key=lambda x: (-int(x["delivers"]), -x["revenue"]))
    return out


def centre_revenue(org: str, since: str | None = None) -> dict:
    """Centre's money in one place — paid invoices, delivered-session value, fulfilled orders. One app, no separate
    billing tool needed."""
    iv_where = "org = ? AND status = 'paid'"
    bk_where = f"org = ? AND status IN {_DELIVERED}"
    iargs: list = [org]
    bargs: list = [org]
    if since:
        iv_where += " AND ts >= ?"; iargs.append(since)
        bk_where += " AND start_ts >= ?"; bargs.append(since)
    invoices = db.one(f"SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS amt FROM c_invoices WHERE {iv_where}", tuple(iargs))
    sessions = db.one(f"SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS amt FROM c_bookings WHERE {bk_where}", tuple(bargs))
    due = db.one("SELECT COALESCE(SUM(total),0) AS amt FROM c_invoices WHERE org = ? AND status = 'due'", (org,))
    orders = db.one("SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS amt FROM orders WHERE org = ? AND status NOT IN ('cancelled')", (org,))
    return {"org": org, "invoiced_paid": invoices["amt"], "invoices_paid_n": invoices["n"],
            "session_revenue": sessions["amt"], "sessions_delivered": sessions["n"],
            "orders_value": orders["amt"], "orders_n": orders["n"], "outstanding": due["amt"],
            "total_revenue": invoices["amt"] + sessions["amt"] + orders["amt"]}


def platform_overview() -> dict:
    """Super-admin: the whole network at a glance — every centre, its people, staff and revenue."""
    init()
    centres = list_centres()
    doctors = [s for s in staffmod.all_staff() if staffmod.ROLES.get(s["role"], {}).get("workspace") == "doctor"]
    rows = []
    tot_rev = tot_patients = 0
    for c in centres:
        rev = centre_revenue(c["slug"])
        n_pat = db.one("SELECT COUNT(DISTINCT patient_id) AS n FROM care_edges WHERE org = ? AND kind='centre' AND status='active'", (c["slug"],))["n"]
        n_staff = db.one("SELECT COUNT(*) AS n FROM staff WHERE org = ? AND active = 1", (c["slug"],))["n"]
        tot_rev += rev["total_revenue"]; tot_patients += n_pat
        rows.append({"slug": c["slug"], "name": c["name"], "city": c["city"], "status": c["status"],
                     "patients": n_pat, "staff": n_staff, "revenue": rev["total_revenue"], "outstanding": rev["outstanding"]})
    return {"centres": len(centres), "doctors": len(doctors), "patients": tot_patients, "total_revenue": tot_rev,
            "rows": rows}
