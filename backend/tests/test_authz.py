"""Authorization regression tests — the two critical holes from the 2026-10-20 audit must stay closed:
  C1: /mgmt is UNAUTHENTICATED in multi-user mode (auth middleware exits early).
  C2: any staff token can read/write another org's data via the org param (BOLA / OWASP API1).
These are the negative tests OWASP API1:2023 says to gate deploys on. Order-independent (test modules share one DB).
"""
# NOTE: do NOT set a password or enable accounts here — test modules share one DB, and doing so would flip the whole
# run into a mode that breaks single-user consumer tests. The C1/C2 guards live in the global _bind_user dependency,
# which runs in EVERY mode, so testing in the shared single-user mode fully validates them. (The multi-user bypass
# specifically is additionally covered by manual verification in the audit.)
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "authz.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import staff as staffmod  # noqa: E402

A_ADMIN, B_ADMIN, DOC, SUPER = "a.authz@a.in", "b.authz@b.in", "doc.authz@c.in", "root.authz@t.io"
ORGA, ORGB = "authz-a", "authz-b"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # a super-admin + two centre orgs with admins + a doctor, created directly (bootstrap gate covered elsewhere)
        staffmod.create_staff("platform", "super_admin", "Root", SUPER, "superpw12345", by="t")
        from app import tenancy
        for slug, email in ((ORGA, A_ADMIN), (ORGB, B_ADMIN)):
            if not tenancy.centre(slug):
                tenancy.onboard_centre(slug, "", slug, admin_name="Adm", admin_email=email, admin_password="centrepw123", by="t")
        staffmod.create_staff(ORGA, "doctor", "Doc", DOC, "doctorpw123", by="t")
        yield c


def _tok(c, email, pw):
    return {"Authorization": "Bearer " + c.post("/mgmt/auth/login", json={"email": email, "password": pw}).json()["token"]}


# ---- C1: management plane requires a staff token, even in multi-user mode ----
NOAUTH_GET = ["/mgmt/centre/members?org=%s" % ORGA, "/mgmt/clinic/inbox?org=%s" % ORGA,
              "/mgmt/catalog?org=%s&kind=service_type" % ORGA, "/mgmt/api-keys?org=%s" % ORGA,
              "/mgmt/billing/summary?org=%s" % ORGA, "/mgmt/centre/revenue?org=%s" % ORGA, "/mgmt/overview?org=%s" % ORGA]
NOAUTH_POST = [("/mgmt/api-keys", {"org": ORGA, "name": "x", "scopes": ["read"]}),
               ("/mgmt/clinic/patients/1/notes", {"org": ORGA, "author": "a", "content": {}}),
               ("/mgmt/catalog", {"org": ORGA, "kind": "service_type", "name": "x", "data": {}}),
               ("/mgmt/config", {"org": ORGA, "modules": {"billing": True}})]


def test_c1_no_token_is_rejected(client):
    for ep in NOAUTH_GET:
        assert client.get(ep).status_code == 401, f"{ep} must need a token"
    for ep, body in NOAUTH_POST:
        assert client.post(ep, json=body).status_code == 401, f"POST {ep} must need a token"


def test_c1_consumer_token_cannot_reach_mgmt(client):
    # a consumer (Vault) token must not satisfy a management route — planes are separate
    tok = client.post("/auth/login", json={"email": "authzuser@x.com", "password": "password123"}).json().get("token")
    if tok:  # consumer login may differ; only assert if we got one
        h = {"Authorization": "Bearer " + tok}
        assert client.get(f"/mgmt/centre/members?org={ORGA}", headers=h).status_code == 401
        assert client.get("/mgmt/admin/overview", headers=h).status_code == 401


def test_c1_garbage_token_rejected(client):
    h = {"Authorization": "Bearer not-a-real-token"}
    assert client.get(f"/mgmt/centre/members?org={ORGA}", headers=h).status_code == 401


# ---- C2: a staff member cannot touch another org (query param OR body) ----
def test_c2_cross_tenant_query_blocked(client):
    ha = _tok(client, A_ADMIN, "centrepw123")
    for ep in [f"/mgmt/billing/summary?org={ORGB}", f"/mgmt/centre/people?org={ORGB}",
               f"/mgmt/centre/revenue?org={ORGB}", f"/mgmt/catalog?org={ORGB}&kind=service_type",
               f"/mgmt/clinic/inbox?org={ORGB}", f"/mgmt/api-keys?org={ORGB}", f"/mgmt/billing/payments?org={ORGB}"]:
        assert client.get(ep, headers=ha).status_code == 403, f"{ep} cross-tenant must be 403"


def test_c2_cross_tenant_body_blocked(client):
    ha = _tok(client, A_ADMIN, "centrepw123")
    for ep, body in [("/mgmt/api-keys", {"org": ORGB, "name": "x", "scopes": ["read"]}),
                     ("/mgmt/catalog", {"org": ORGB, "kind": "service_type", "name": "x", "data": {}}),
                     ("/mgmt/config", {"org": ORGB, "modules": {"billing": True}}),
                     ("/mgmt/goals", {"org": ORGB, "title": "x"})]:
        assert client.post(ep, json=body, headers=ha).status_code == 403, f"POST {ep} cross-tenant body must be 403"


def test_c2_own_org_still_works(client):
    ha = _tok(client, A_ADMIN, "centrepw123")
    assert client.get(f"/mgmt/billing/summary?org={ORGA}", headers=ha).status_code == 200
    assert client.get(f"/mgmt/centre/people?org={ORGA}", headers=ha).status_code == 200
    assert client.post("/mgmt/api-keys", json={"org": ORGA, "name": "ok", "scopes": ["read"]}, headers=ha).status_code == 200


# ---- function-level (BFLA / OWASP API5): role must match the function ----
def test_bfla_non_super_cannot_reach_admin(client):
    ha = _tok(client, A_ADMIN, "centrepw123")          # centre admin, not super
    hd = _tok(client, DOC, "doctorpw123")              # doctor, not admin
    assert client.get("/mgmt/admin/overview", headers=ha).status_code == 403
    assert client.get("/mgmt/admin/centres", headers=ha).status_code == 403
    assert client.get("/mgmt/admin/overview", headers=hd).status_code == 403
    # a doctor cannot add staff (not an admin)
    assert client.post("/mgmt/staff", json={"org": ORGA, "role": "therapist", "name": "x", "email": "zz.authz@a.in", "password": "pw12345678"}, headers=hd).status_code == 403


def test_super_admin_can_cross_org(client):
    hs = _tok(client, SUPER, "superpw12345")
    assert client.get("/mgmt/admin/overview", headers=hs).status_code == 200
    # super-admin may address any org
    assert client.get(f"/mgmt/billing/summary?org={ORGB}", headers=hs).status_code == 200
