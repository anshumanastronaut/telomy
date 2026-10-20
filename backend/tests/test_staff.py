"""Role-based staff auth: platform / centre / doctor log in separately, land in different workspaces, and privilege
boundaries hold (a centre admin can't mint doctors or super-admins)."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import staff as staffmod  # noqa: E402

# Unique identities — test modules share one DB in a pytest run, so this file must be order-independent.
SUPER, CADMIN, DOC, SLUG = "root.stf@telomy.io", "maya.stf@zen.in", "rao.stf@clinic.in", "zen-stf"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_bootstrap_gate(client):
    # once any staff exist, open signup is closed — it needs an admin token
    staffmod.create_staff("platform", "super_admin", "Seed", "seed.stf@telomy.io", "superpw12345", by="test")
    r = client.post("/mgmt/auth/signup", json={"org": "x", "role": "centre_admin", "name": "Nope", "email": "nope.stf@x.in", "password": "pw12345678"})
    assert r.status_code == 403


def test_separate_logins_roles_and_boundaries(client):
    # platform super-admin (created directly — the bootstrap gate itself is covered above)
    staffmod.create_staff("platform", "super_admin", "Root", SUPER, "superpw12345", by="test")
    ls = client.post("/mgmt/auth/login", json={"email": SUPER, "password": "superpw12345"}).json()
    assert ls["workspace"] == "platform" and ls["admin"]
    hs = {"Authorization": "Bearer " + ls["token"]}

    # super-admin onboards a centre (this creates the centre_admin login)
    c = client.post("/mgmt/admin/centres", json={"name": "Zen Longevity", "city": "Pune", "slug": SLUG,
                                                 "admin_name": "Maya", "admin_email": CADMIN, "admin_password": "centrepw123"}, headers=hs).json()
    assert c["slug"] == SLUG and c["admin"]["role"] == "centre_admin"

    # centre admin logs in -> CENTRE workspace
    la = client.post("/mgmt/auth/login", json={"email": CADMIN, "password": "centrepw123"}).json()
    assert la["workspace"] == "centre" and la["admin"]
    ha = {"Authorization": "Bearer " + la["token"]}

    # a centre admin CAN add centre-side staff (a therapist) ...
    assert client.post("/mgmt/staff", json={"org": SLUG, "role": "therapist", "name": "Tara", "email": "tara.stf@zen.in", "password": "therapypw1"}, headers=ha).status_code == 200
    # ... but CANNOT create a doctor-side account or a super-admin (privilege boundary)
    assert client.post("/mgmt/staff", json={"org": SLUG, "role": "doctor", "name": "X", "email": "x.stf@zen.in", "password": "pw12345678"}, headers=ha).status_code == 403
    assert client.post("/mgmt/staff", json={"org": SLUG, "role": "super_admin", "name": "Y", "email": "y.stf@zen.in", "password": "pw12345678"}, headers=ha).status_code == 403

    # only the super-admin mints doctors
    doc = client.post("/mgmt/admin/doctors", json={"name": "Dr. Rao", "email": DOC, "password": "doctorpw123", "org": SLUG}, headers=hs).json()
    assert doc["role"] == "doctor"
    ld = client.post("/mgmt/auth/login", json={"email": DOC, "password": "doctorpw123"}).json()
    assert ld["workspace"] == "doctor" and ld["admin"] is False
    hd = {"Authorization": "Bearer " + ld["token"]}

    # /me reflects the right role for each token
    assert client.get("/mgmt/auth/me", headers=ha).json()["role"] == "centre_admin"
    assert client.get("/mgmt/auth/me", headers=hd).json()["workspace"] == "doctor"
    # a doctor is not an admin -> cannot add staff; a non-super cannot see the platform overview
    assert client.post("/mgmt/staff", json={"org": SLUG, "role": "doctor", "name": "Z", "email": "z.stf@zen.in", "password": "pw12345678"}, headers=hd).status_code == 403
    assert client.get("/mgmt/admin/overview", headers=ha).status_code == 403
    assert client.get("/mgmt/admin/overview", headers=hs).status_code == 200

    # bad login + duplicate email
    assert client.post("/mgmt/auth/login", json={"email": CADMIN, "password": "nope"}).status_code == 401
    assert client.post("/mgmt/staff", json={"org": SLUG, "role": "therapist", "name": "dup", "email": "tara.stf@zen.in", "password": "pw12345678"}, headers=ha).status_code == 400
    # logout revokes
    client.post("/mgmt/auth/logout", headers=hd)
    assert client.get("/mgmt/auth/me", headers=hd).status_code == 401
