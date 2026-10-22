"""Longitudinal vitals store — ingest, idempotency, downsampled series, day timeline."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_ingest_and_series(client):
    t0 = 1_793_000_000
    batch = [{"ts": t0 + i * 5, "metric": "hr", "value": 60 + (i % 10), "step_s": 5} for i in range(720)]  # 1h at 5s
    r = client.post("/vitals/ingest", json={"samples": batch, "source": "patch"}).json()
    assert r["stored"] == 720
    # idempotent re-sync
    assert client.post("/vitals/ingest", json={"samples": batch, "source": "patch"}).json()["stored"] == 720
    s = client.get("/vitals/series", params={"metric": "hr", "start": t0, "end": t0 + 3600, "max_points": 60}).json()
    assert s["n"] == 720 and len(s["points"]) <= 61 and s["sources"] == ["patch"]
    cov = client.get("/vitals/coverage", params={"days": 3650}).json()
    assert any(b["source"] == "patch" and b["hours"] >= 0.9 for b in cov["by_source"])


def test_bad_samples_ignored(client):
    r = client.post("/vitals/ingest", json={"samples": [{"ts": "x"}, {"metric": "hr"}, {"ts": 999, "metric": "hr", "value": 5}], "source": "ring"}).json()
    assert r["stored"] == 0
