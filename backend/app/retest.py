"""Closed-loop retest (Track B4) — the "measure → act → re-measure" loop Superpower/Function build retention on.

From the member's own report history we work out, per marker: when it was last tested, when it is next due (sooner
when it's out of optimal, since those are the ones you act on), and whether it has improved or worsened since the
previous draw (direction-aware). The app turns this into: what to retest now, what changed since last time, and the
upcoming schedule. Wellness information — cadence suggestions, not medical orders.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import catalog, catalog_ext, engine

MARKERS = catalog.MARKERS
_PREP = getattr(catalog_ext, "RETEST_PREP", {})

# marker groups that move fast and are acted on → short interval when out of optimal
_ACTIONABLE = {"chol_total", "ldl", "hdl", "tg", "apob", "lpa", "glucose", "hba1c", "insulin",
               "hscrp", "homocysteine", "vitd", "b12", "ferritin", "uric_acid"}
_STABLE = {"egfr", "creatinine", "alt", "ggt", "alp", "tsh", "hemoglobin", "wbc", "testosterone", "cortisol"}


def _interval_days(mid: str, panel: str, in_optimal: bool) -> int | None:
    """Suggested days to the next test; None = one-time (e.g. genetics)."""
    if panel in ("genetic",):
        return None
    if panel == "bioage":
        return 365
    if mid in _ACTIONABLE:
        return 90 if not in_optimal else 180
    if mid in _STABLE:
        return 180 if not in_optimal else 365
    return 180 if not in_optimal else 365


def _improved(better: str, old: float, new: float, low, high) -> bool | None:
    if old is None or new is None:
        return None
    if better == "low":
        return new < old
    if better == "high":
        return new > old
    if better == "mid" and low is not None and high is not None:
        mid = (low + high) / 2
        return abs(new - mid) < abs(old - mid)
    return None


def plan(as_of: str | None = None) -> dict:
    today = date.fromisoformat(as_of or engine.now_iso()[:10])
    have = engine.latest_values(as_of)
    due, changes, schedule = [], [], []

    for mid in have:
        spec = MARKERS.get(mid)
        if not spec:
            continue
        hist = engine.marker_history(mid)
        if not hist:
            continue
        last = hist[-1]
        in_optimal = last.get("status") == "optimal"
        interval = _interval_days(mid, spec[1], in_optimal)
        name, unit, better, low, high = spec[0], spec[2], spec[5], spec[3], spec[4]

        last_day = date.fromisoformat(last["collected_on"])
        days_old = (today - last_day).days

        # before / after since the previous draw
        t = engine.marker_trend(mid)
        if t and t.get("delta") is not None:
            imp = _improved(better, t.get("from"), last.get("value_num"), low, high)
            if imp is not None and abs(t["delta"]) > 0:
                changes.append({
                    "id": mid, "name": name, "unit": unit, "from": t["from"], "to": last.get("value_num"),
                    "delta": round(t["delta"], 2), "improved": imp, "from_day": t.get("from_day"),
                    "status": last.get("status"),
                })

        if interval is None:
            continue
        next_due = last_day + timedelta(days=interval)
        overdue_days = (today - next_due).days
        row = {"id": mid, "name": name, "unit": unit, "last_value": last.get("value_num"),
               "last_tested": last["collected_on"], "days_old": days_old, "interval_days": interval,
               "next_due": next_due.isoformat(), "status": last.get("status"), "prep": _PREP.get(mid)}
        schedule.append(row)
        if overdue_days >= 0:
            due.append({**row, "overdue_days": overdue_days})

    due.sort(key=lambda r: r["overdue_days"], reverse=True)
    schedule.sort(key=lambda r: r["next_due"])
    improving = [c for c in changes if c["improved"]]
    worsening = [c for c in changes if not c["improved"]]
    return {
        "due": due,
        "improving": sorted(improving, key=lambda c: abs(c["delta"]), reverse=True),
        "worsening": sorted(worsening, key=lambda c: abs(c["delta"]), reverse=True),
        "schedule": schedule,
        "counts": {"due": len(due), "improving": len(improving), "worsening": len(worsening)},
        "note": ("Retest cadence is a suggestion based on each marker and whether it's in your optimal range — not a "
                 "medical order. Act on out-of-range markers with your clinician, then re-measure to see what worked."),
    }
