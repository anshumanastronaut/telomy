"""Science registry — new findings added as data flow into the engine."""
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


def test_add_rule_fires_insight(client):
    from app import science, engine, seed
    M = lambda k, v, lo, hi: {"marker_id": k, "value": v, "unit": "mg/dL", "ref_low": lo, "ref_high": hi,  # noqa: E731
                              "ref_text": "", "flag": None, "status": "out_of_range" if v > hi else "in_range"}
    seed.save_report({"title": "sci test", "panel": "blood", "collected_on": "2099-02-02", "is_test_data": True,
                      "markers": [M("apob", 120, 40, 90)]}, "t", "")
    f = science.add_finding("cross_panel_rule", {"conditions": [{"marker": "apob", "op": "high"}],
        "title": "ApoB high (registry rule)", "body": "ApoB {apob}.", "markers": ["apob"], "confidence": 0.7},
        citation="Test 2026", evidence="A")
    assert any(i["id"] == engine._iid("science", f["id"]) for i in engine.list_insights())
    # deactivate -> gone
    science.set_active(f["id"], False)
    assert not any(i["id"] == engine._iid("science", f["id"]) for i in engine.list_insights())


def test_marker_range_override(client):
    from app import science
    base = science.effective_range("ldl")
    science.add_finding("marker_range", {"marker": "ldl", "high": 70}, citation="guideline", evidence="A")
    assert science.effective_range("ldl")[1] == 70 and science.effective_range("ldl") != base


def test_cellular_effect_added_as_data(client):
    from app import science, cellular
    science.add_finding("cellular_effect", {"kind": "supplement", "name": "Test-Nutrient", "terms": ["testnutrient"],
        "cells": "x", "site": "mitochondria", "pathway": "p", "mechanism": "m", "markers": ["hrv"], "direction": "up"},
        citation="Paper 2026", evidence="C")
    assert any(e["name"] == "Test-Nutrient" for e in cellular.explain("I took testnutrient"))


def test_bad_input_rejected(client):
    assert client.post("/science", json={"kind": "cross_panel_rule", "payload": {"conditions": [{"marker": "nope", "op": "high"}]}, "citation": "x"}).status_code == 400
    assert client.post("/science", json={"kind": "marker_range", "payload": {"marker": "ldl", "high": 70}, "citation": "x", "evidence": "Z"}).status_code == 400
