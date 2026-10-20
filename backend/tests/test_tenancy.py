"""The care graph connects end-to-end: super-admin onboards a centre + doctors; a doctor intakes a patient and assigns
them to a centre; a centre onboards a user and assigns them to a doctor; operational staff get duties; and performance
and revenue roll up from the booking ledger with no separate bookkeeping."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "tenancy.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import staff as staffmod  # noqa: E402

# Unique identifiers so this file is order-independent even when test modules share one DB.
SUPER = "root.tnc@t.io"
CADMIN = "ava.tnc@halo.in"
DOC = "sen.tnc@clinic.in"
THER = "tom.tnc@halo.in"
SLUG = "halo-tnc"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _h(tok):
    return {"Authorization": "Bearer " + tok}


def test_care_graph_connects(client):
    # platform super-admin — created directly (the signup gate is covered in test_staff); this file may not be first
    staffmod.create_staff("platform", "super_admin", "Root", SUPER, "superpw12345", by="test")
    hs = _h(client.post("/mgmt/auth/login", json={"email": SUPER, "password": "superpw12345"}).json()["token"])

    # onboard a centre with its admin
    client.post("/mgmt/admin/centres", json={"name": "Halo TNC", "slug": SLUG, "city": "BLR",
                "admin_name": "Ava", "admin_email": CADMIN, "admin_password": "centrepw123"}, headers=hs)
    hc = _h(client.post("/mgmt/auth/login", json={"email": CADMIN, "password": "centrepw123"}).json()["token"])

    # super-admin mints a doctor and affiliates them to the centre
    doc = client.post("/mgmt/admin/doctors", json={"name": "Dr. Sen", "email": DOC, "password": "doctorpw123", "org": SLUG}, headers=hs).json()
    hd = _h(client.post("/mgmt/auth/login", json={"email": DOC, "password": "doctorpw123"}).json()["token"])
    assert any(d["id"] == doc["id"] for d in client.get(f"/mgmt/centre/doctors?org={SLUG}", headers=hc).json())

    # DOCTOR intakes a patient and assigns them to the centre
    p = client.post("/mgmt/patients/onboard", json={"name": "Ravi TNC", "age": 44, "sex": "male", "org": SLUG}, headers=hd).json()
    pid = p["patient_id"]
    g = client.get(f"/mgmt/patients/{pid}/graph", headers=hd).json()
    assert g["centre"]["slug"] == SLUG
    # the centre now sees Ravi among its people
    assert any(x["id"] == pid for x in client.get(f"/mgmt/centre/people?org={SLUG}", headers=hc).json())

    # CENTRE onboards a walk-in and assigns them to the doctor
    p2 = client.post("/mgmt/patients/onboard", json={"name": "Nina TNC", "age": 51, "sex": "female", "doctor_id": doc["id"]}, headers=hc).json()
    assert any(x["id"] == p2["patient_id"] for x in client.get("/mgmt/doctor/patients", headers=hd).json())

    # centre adds a therapist + a therapy (service_type), then assigns the duty
    th = client.post("/mgmt/staff", json={"org": SLUG, "role": "therapist", "name": "Tom", "email": THER, "password": "therapypw1"}, headers=hc).json()
    svc = client.post("/mgmt/catalog", json={"org": SLUG, "kind": "service_type", "name": "Infrared sauna", "data": {"minutes": 30, "price": 900}}, headers=hc).json()
    client.post("/mgmt/duties", json={"org": SLUG, "staff_id": th["id"], "duty_kind": "service", "ref_id": svc["id"]}, headers=hc)
    duties = client.get(f"/mgmt/duties?org={SLUG}&staff_id={th['id']}", headers=hc).json()
    assert duties and duties[0]["ref_id"] == svc["id"]

    # privilege: a non-admin doctor cannot add duties
    assert client.post("/mgmt/duties", json={"org": SLUG, "staff_id": th["id"], "duty_kind": "service", "ref_id": svc["id"]}, headers=hd).status_code == 403

    # performance + revenue endpoints respond and include our therapist
    perf = client.get(f"/mgmt/centre/performance?org={SLUG}", headers=hc).json()
    assert any(row["staff_id"] == th["id"] for row in perf)
    rev = client.get(f"/mgmt/centre/revenue?org={SLUG}", headers=hc).json()
    assert set(["total_revenue", "outstanding", "session_revenue"]).issubset(rev.keys())

    # platform overview rolls the centre up
    ov = client.get("/mgmt/admin/overview", headers=hs).json()
    assert ov["centres"] >= 1 and any(r["slug"] == SLUG for r in ov["rows"])
