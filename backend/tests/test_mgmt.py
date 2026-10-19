"""Modular centre + clinic platform: customise config, then run the operational flow."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_configure_and_run_centre(client):
    # 1) a centre turns modules on and brands itself
    cfg = client.post("/mgmt/config", json={"org": "zen", "kind": "centre", "modules": {"memberships": True, "inventory": True},
                                            "branding": {"name": "Zen Wellness", "primary": "#2aa"}}).json()
    assert cfg["branding"]["name"] == "Zen Wellness" and cfg["modules"]["memberships"]
    # 2) add a custom therapy/service type and a membership plan — no code
    svc = client.post("/mgmt/catalog", json={"org": "zen", "kind": "service_type", "name": "Cryotherapy",
                                             "data": {"minutes": 15, "price": 1500, "category": "recovery"}}).json()
    plan = client.post("/mgmt/catalog", json={"org": "zen", "kind": "membership_plan", "name": "Recovery 10-pack",
                                             "data": {"price": 12000, "cycle_days": 60, "credits": 10}}).json()
    assert client.post("/mgmt/catalog", json={"org": "zen", "kind": "bogus", "name": "x"}).status_code == 400
    # 3) a custom field on members
    client.post("/mgmt/fields", json={"org": "zen", "entity": "member", "label": "Goal", "type": "select",
                                      "options": ["recovery", "performance", "longevity"], "required": True})
    form = client.get("/mgmt/form", params={"org": "zen", "entity": "member"}).json()
    assert any(f["label"] == "Goal" for sec in form["sections"] for f in sec["fields"])
    # required custom field enforced
    assert client.post("/mgmt/centre/members", json={"org": "zen", "name": "No Goal"}).status_code == 400
    m = client.post("/mgmt/centre/members", json={"org": "zen", "name": "Asha", "fields": {"goal": "recovery"}}).json()
    # 4) enroll in the plan (creates an invoice), then book + check-in spends a credit
    ms = client.post(f"/mgmt/centre/members/{m['id']}/enroll", json={"org": "zen", "plan_id": plan["id"]}).json()
    assert ms["credits_left"] == 10
    b = client.post("/mgmt/centre/book", json={"org": "zen", "member_id": m["id"], "service_id": svc["id"],
                                              "start_ts": "2026-11-01T10:00:00", "resource_id": 7}).json()
    # resource double-book is refused
    assert client.post("/mgmt/centre/book", json={"org": "zen", "member_id": m["id"], "service_id": svc["id"],
                                                  "start_ts": "2026-11-01T10:05:00", "resource_id": 7}).status_code == 400
    ci = client.post(f"/mgmt/centre/bookings/{b['id']}/checkin").json()
    assert ci["status"] == "checked_in"
    assert client.get(f"/mgmt/centre/members/{m['id']}").json()["memberships"][0]["credits_left"] == 9
    dash = client.get("/mgmt/centre/dashboard", params={"org": "zen"}).json()
    assert dash["active_members"] >= 1 and dash["today_bookings"] >= 0


def test_clinic_notes_and_tasks(client):
    # default SOAP template appears; a note from it; a task
    t = client.get("/mgmt/clinic/templates", params={"org": "clin"}).json()
    assert any(x["key"] == "soap" for x in t)
    n = client.post("/mgmt/clinic/patients/1/notes", json={"org": "clin", "author": "Dr. Rao", "template_id": t[0]["id"],
                                                           "title": "Follow-up", "content": {"s": "feels better", "a": "improving"}}).json()
    assert n["content"]["s"] == "feels better" and n["signed"] == 0
    signed = client.post(f"/mgmt/clinic/notes/{n['id']}/sign", json={"by": "Dr. Rao"}).json()
    assert signed["signed"] == 1
    tk = client.post("/mgmt/clinic/tasks", json={"org": "clin", "text": "Review Asha's labs", "priority": 2}).json()
    assert any(x["id"] == tk["id"] for x in client.get("/mgmt/clinic/tasks", params={"org": "clin"}).json())
    inbox = client.get("/mgmt/clinic/inbox", params={"org": "clin"}).json()
    assert "patients" in inbox and "open_tasks" in inbox and inbox["templates"]
