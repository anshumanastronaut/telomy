"""Cellular-effects knowledge base."""
from app import cellular


def test_explain_matches_intervention():
    omega = cellular.explain("I started omega-3 fish oil")
    assert omega and omega[0]["name"].startswith("Omega-3")
    assert "tg" in omega[0]["markers"] and omega[0]["evidence"] in ("A", "B", "C", "D")


def test_for_marker_links_biology():
    names = {e["name"] for e in cellular.for_marker("apob")}
    assert any("Statin" in n for n in names) and any("Saturated" in n for n in names)
    assert len(cellular.for_marker("hrv")) >= 5


def test_every_effect_is_wellformed():
    from app.catalog import MARKERS
    from app.engine import SIGNALS
    known = set(MARKERS) | set(SIGNALS) | {"calcium"}
    for e in cellular.EFFECTS:
        assert e["evidence"] in ("A", "B", "C", "D") and e["citation"]
        for m in e["markers"]:
            assert m in known, f"{e['name']} references unknown marker {m}"


def test_cards_cover_all():
    assert len(cellular.cards()) == len(cellular.EFFECTS)
