"""Circadian engine — cosinor fit, phase/nadir recovery, fault diagnosis and fixes."""
import math
import datetime as dt
from app import circadian as c


def _gen(nadir_h, amp=12, mesor=62, days=3, flat=False, step_min=10):
    pts, base, acro = [], dt.datetime(2026, 10, 20, 0, 0, tzinfo=c.IST).timestamp(), (nadir_h + 12) % 24
    n = days * (1440 // step_min)
    for i in range(n):
        t = base + i * step_min * 60
        h = ((t - base) / 3600) % 24
        a = 1.0 if not flat else 0.05
        pts.append([t, mesor + a * amp * math.cos(2 * math.pi * (h - acro) / 24)])  # noise-free for determinism
    return pts


def test_cosinor_recovers_nadir_and_amplitude():
    fit = c.cosinor(_gen(4.0, amp=10, mesor=60))
    assert abs(fit["nadir_h"] - 4.0) < 0.3          # recovers the trough time
    assert abs(fit["amplitude"] - 10) < 1.0
    assert fit["r2"] > 0.95


def test_healthy_rhythm_is_aligned():
    r = c.assess({"hr": _gen(4.0)}, target_wake_h=6.5)
    assert r["status"] == "ok"
    assert r["alignment"]["verdict"] == "aligned"
    assert r["faults"] == []


def test_delayed_phase_flagged_with_morning_light_fix():
    r = c.assess({"hr": _gen(8.0)}, target_wake_h=6.5)
    assert any(f["fault"] == "delayed_phase" for f in r["faults"])
    assert any("light" in f["lever"].lower() for f in r["fixes"])


def test_advanced_phase_flagged():
    r = c.assess({"hr": _gen(1.0)}, target_wake_h=6.5)
    assert any(f["fault"] == "advanced_phase" for f in r["faults"])


def test_low_amplitude_flagged_when_flat():
    # a tiny day-night swing (flat clock) must be flagged even when the fit is clean (high R²)
    r = c.assess({"hr": _gen(4.0, flat=True)}, target_wake_h=6.5)
    assert r["rhythm"]["amplitude"] < 2
    assert any(f["fault"] == "low_amplitude" for f in r["faults"])
    assert r["alignment"]["verdict"] == "misaligned"


def test_social_jetlag():
    base = dt.datetime(2026, 10, 20, 0, 0, tzinfo=c.IST).timestamp()
    wins = [
        {"start": base + 23 * 3600, "end": base + 30 * 3600, "workday": True},    # ~23:00–06:00 weekday
        {"start": base + 24 * 3600 + 2 * 3600, "end": base + 24 * 3600 + 11 * 3600, "workday": False},  # ~02:00–11:00 weekend
    ]
    sj = c.social_jetlag(wins)
    assert sj and sj["hours"] >= 1.5 and sj["severity"] in ("moderate", "high")


def test_insufficient_data():
    assert c.assess({})["status"] == "insufficient_data"
    assert c.assess({"hr": [[1, 60], [2, 61]]})["status"] == "insufficient_data"


def test_no_lifespan_or_diagnosis_overclaim():
    r = c.assess({"hr": _gen(8.0)})
    assert "not a diagnosis" in r["disclaimer"].lower()
