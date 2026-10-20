"""Multi-age engine — the methods run and are internally consistent on seeded data."""
import os, tempfile
os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_bioage_runs_on_seed(client):
    r = client.get("/bioage").json()
    assert r["ok"] and r["chronological_age"] > 0
    # at least PhenoAge or KDM should be computable from the seeded labs
    b = r["blood"]
    assert b["phenoage"]["available"] or (b["kdm"] and b["kdm"].get("available"))
    if b["kdm"] and b["kdm"].get("available"):
        assert 10 < b["kdm"]["value"] < 100 and b["kdm"]["markers_used"] >= 4


def test_kdm_params_loaded():
    from app import bioage
    p = bioage._params()
    assert p.get("kdm") and p["kdm"]["params"] and "sbp" in p["kdm"]["params"]
    assert p["validation"]["kdm_r"] > 0.9   # the NHANES-fitted model correlates with chronological age
