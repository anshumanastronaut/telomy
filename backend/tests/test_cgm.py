"""Nightscout-compatible CGM receiver — synthetic readings only."""
import hashlib
import os
import tempfile

os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
os.environ["TELOMY_NIGHTSCOUT_SECRET"] = "test-ns-secret-123"
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

H = {"api-secret": hashlib.sha1(b"test-ns-secret-123").hexdigest()}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_nightscout_upload_and_tir(client):
    assert client.get("/nightscout/api/v1/status.json").status_code == 401
    assert client.get("/nightscout/api/v1/status.json", headers=H).json()["status"] == "ok"
    t0 = 1792300000 * 1000
    items = [{"type": "sgv", "sgv": 100 + (40 if 100 <= i < 130 else 0), "date": t0 + i * 300000, "direction": "Flat"} for i in range(300)]
    items.append({"type": "mbg", "mbg": 120})                                     # non-sgv ignored
    assert client.post("/nightscout/api/v1/entries", json=items, headers=H).json()["n"] == 300
    assert len(client.get("/nightscout/api/v1/entries.json", params={"count": 5}, headers=H).json()) == 5
    s = client.get("/cgm/summary", params={"days": 3650}).json()
    assert s["ok"] and s["tir"] == 100.0 and 100 <= s["mean"] <= 115 and s["gmi"] > 5
