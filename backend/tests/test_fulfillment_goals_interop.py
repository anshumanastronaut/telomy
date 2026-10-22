"""Fulfillment, goals, and interoperability."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import staff as staffmod  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # /mgmt now requires a staff token; a super-admin can address any org (C2-exempt).
        try:
            staffmod.create_staff("platform", "super_admin", "Root", "root.fgi@t.io", "superpw12345", by="t")
        except Exception:
            pass
        tok = c.post("/mgmt/auth/login", json={"email": "root.fgi@t.io", "password": "superpw12345"}).json()["token"]
        c.headers.update({"Authorization": "Bearer " + tok})
        yield c


def test_fulfillment_flow(client):
    # supplement delivery
    o = client.post("/mgmt/orders", json={"org": "z", "kind": "supplement", "items": [{"name": "Vitamin D3", "qty": 1, "price": 400}], "address": "Home"}).json()
    assert o["direction"] == "delivery" and o["total"] == 400 and o["status"] == "created"
    o2 = client.post(f"/mgmt/orders/{o['id']}/advance", json={"status": "dispatched", "tracking": "TRK1"}).json()
    assert o2["status"] == "dispatched" and o2["tracking"] == "TRK1"
    # bad status for a delivery flow
    assert client.post(f"/mgmt/orders/{o['id']}/advance", json={"status": "collected"}).status_code == 400
    # medicine requires a signed Rx
    assert client.post("/mgmt/orders", json={"org": "z", "kind": "medicine", "items": [{"name": "X"}]}).status_code == 400
    # lab sample pickup
    p = client.post("/mgmt/sample-pickup", json={"org": "z", "patient_id": 1, "tests": ["CBC", "Lipid"], "address": "Home", "slot": "2026-11-02T08:00"}).json()
    assert p["direction"] == "pickup" and p["status"] == "confirmed"


def test_goals(client):
    g = client.post("/mgmt/goals", json={"org": "z", "title": "Lower resting heart rate", "owner_kind": "member", "owner_id": 1,
                                         "metric": "rhr", "target": 52}).json()
    assert g["title"].startswith("Lower") and g["metric_kind"] == "signal" and g["direction"] == "low"
    free = client.post("/mgmt/goals", json={"org": "z", "title": "Feel more energetic"}).json()
    assert free["metric"] is None and free["pct"] is None
    assert len(client.get("/mgmt/goals", params={"org": "z"}).json()) >= 2
    done = client.post(f"/mgmt/goals/{g['id']}", json={"status": "achieved"}).json()
    assert done["status"] == "achieved"


def test_interop(client):
    # FHIR export shapes
    pat = client.get("/interop/fhir/Patient").json()
    assert pat["resourceType"] == "Patient"
    b = client.get("/interop/fhir/Bundle").json()
    assert b["resourceType"] == "Bundle" and b["entry"][0]["resource"]["resourceType"] == "Patient"
    # api key (shown once), then usable via verify
    k = client.post("/mgmt/api-keys", json={"org": "z", "name": "EHR link", "scopes": ["read"]}).json()
    assert k["key"] and k["prefix"]
    from app import interop
    assert interop.verify_key(k["key"])["org"] == "z" and interop.verify_key("nope") is None
    # webhook registration
    w = client.post("/mgmt/webhooks", json={"org": "z", "url": "https://example.com/hook", "events": ["order.updated"]}).json()
    assert w["secret"] and any(x["id"] == w["id"] for x in client.get("/mgmt/webhooks", params={"org": "z"}).json())
