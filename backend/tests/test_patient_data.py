"""Patient intake (biomarker auto-pull) + the 360 overview + grounded AI summary."""
from app import patient_data as pd


def test_biomarkers_shape_and_source():
    b = pd.biomarkers(1)
    assert set(b) >= {"markers", "raw", "source", "as_of"}
    assert isinstance(b["markers"], dict)
    assert b["source"] in ("live_vault", "seed")


def test_biomarkers_are_engine_keyed():
    # whatever is present must use the keys the longevity/macros/assess engines expect, not raw marker ids
    b = pd.biomarkers(1)
    allowed = set(pd._MARKER_MAP.values()) | {"sex", "age", "height_cm", "weight_kg", "sbp"}
    assert set(b["markers"]) <= allowed, set(b["markers"]) - allowed


def test_unknown_patient_degrades_gracefully():
    b = pd.biomarkers(999999)
    assert b["markers"] == {} or b["source"] == "seed"


def test_overview_structure():
    o = pd.overview(1)
    assert "patient" in o and "ai_summary" in o
    for k in ("biomarkers", "vitals", "recovery_sleep", "habits", "risk_models", "reports", "data_sources"):
        assert k in o, f"overview missing {k}"
    assert o["ai_summary"]["text"]
    assert "diagnosis" in o["ai_summary"]["disclaimer"].lower()


def test_ai_summary_is_grounded_not_model_sourced():
    o = pd.overview(1)
    assert "grounded composer" in o["ai_summary"]["drafted_by"].lower()


def test_overview_me_runs_on_current_db():
    o = pd.overview_me()
    assert "patient" in o and o["patient"]["id"] == "me"
    assert "ai_summary" in o and o["ai_summary"]["text"]


def test_vitals_and_recovery_degrade_when_no_wearable():
    v = pd.vitals_summary(999999)
    assert v["available"] is False
    r = pd.recovery_sleep(999999)
    assert r["available"] is False
