"""Multi-user: per-user databases, auth, and isolation. Uses an isolated TELOMY_DATA_DIR so other suites stay single-user."""
import os
import tempfile

os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "legacy.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app.accounts as acc  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _isolated_accounts():
    prev = os.environ.get("TELOMY_DATA_DIR")
    os.environ["TELOMY_DATA_DIR"] = tempfile.mkdtemp()
    yield
    if prev is None:
        os.environ.pop("TELOMY_DATA_DIR", None)
    else:
        os.environ["TELOMY_DATA_DIR"] = prev


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_signup_login_and_isolation(client):
    assert client.get("/health").status_code == 200           # single-user until first account
    a = client.post("/auth/signup", json={"email": "alice@example.com", "password": "alicepw123", "name": "Alice"}).json()
    b = client.post("/auth/signup", json={"email": "bob@example.com", "password": "bobpw12345", "name": "Bob"}).json()
    assert a["user_id"] != b["user_id"] and a["token"] != b["token"]
    ha = {"Authorization": f"Bearer {a['token']}"}
    hb = {"Authorization": f"Bearer {b['token']}"}
    assert client.get("/profile").status_code == 401          # multi-user on: auth now required
    client.put("/profile", json={"first_name": "Alice", "sex": "female", "height_cm": 165}, headers=ha)
    client.put("/profile", json={"first_name": "Bob", "sex": "male", "height_cm": 180}, headers=hb)
    assert client.get("/profile", headers=ha).json()["first_name"] == "Alice"
    assert client.get("/profile", headers=hb).json()["first_name"] == "Bob"
    assert os.path.exists(acc.user_db_path(a["user_id"])) and acc.user_db_path(a["user_id"]) != acc.user_db_path(b["user_id"])


def test_bad_login_and_dupe(client):
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/auth/signup", json={"email": "alice@example.com", "password": "another123"}).status_code == 400
    assert client.post("/auth/signup", json={"email": "x", "password": "short"}).status_code == 400


def test_logout_revokes(client):
    s = client.post("/auth/signup", json={"email": "carol@example.com", "password": "carolpw123"}).json()
    h = {"Authorization": f"Bearer {s['token']}"}
    assert client.get("/profile", headers=h).status_code == 200
    client.post("/auth/logout", headers=h)
    assert client.get("/profile", headers=h).status_code == 401
