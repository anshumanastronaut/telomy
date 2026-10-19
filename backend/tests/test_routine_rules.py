"""Routine-panel rules fire on a routine report (synthetic values, newest report wins)."""
import os
import tempfile

os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_routine_rules_fire(client):
    from app import seed
    from app.routine_rules import routine_patterns
    M = lambda k, v, u, lo, hi: {"marker_id": k, "value": v, "unit": u, "ref_low": lo, "ref_high": hi,  # noqa: E731
                                 "status": "out_of_range" if (lo is not None and v < lo) or (hi is not None and v > hi) else "in_range"}
    seed.save_report({"title": "Synthetic routine panel", "panel": "blood", "collected_on": "2099-01-01", "is_test_data": True, "markers": [
        M("platelets", 101, "10³/µL", 150, 410), M("mpv", 14.1, "fL", 7, 13), M("anc", 1500, "/mm³", 2000, 7000),
        M("hemoglobin", 14.8, "g/dL", 13, 17), M("mcv", 81, "fL", 83, 101), M("alp", 35, "U/L", 38, 126),
        M("eos_pct", 0.5, "%", 1, 6), M("lymph_pct", 52, "%", 20, 40), M("mentzer", 15.6, "", None, None)]}, "test", "")
    titles = {i["title"] for i in routine_patterns()}
    assert any(t.startswith("Two blood cell lines") for t in titles)
    assert "Platelets are fewer but larger than usual" in titles
    assert "Red cells are slightly small, without anaemia" in titles
    assert "Alkaline phosphatase is slightly low" in titles
    assert any("other value" in t for t in titles)
