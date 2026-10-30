"""Cross-device calibration from the longitudinal vitals (vitals_ts).

Every device the user wears — chest patch, ring, JCVital, Galaxy Watch, WHOOP — syncs HR / SpO2 / skin-temp into ONE
tall table keyed (ts, metric, source). Because the user wears everything on the same body at the same time, the table
holds simultaneous readings from every device. Here we pair each device against the most accurate REFERENCE for a
metric (the chest ECG patch is the HR/HRV truth) within a small time tolerance, and fit a per-device calibration:
bias, error (MAE/RMSE), correlation, and a linear correction (slope·device + intercept → reference).

This is the engine-improvement loop: measure how each device deviates from truth, derive a correction, validate.
It runs continuously on whatever has synced; it needs no lab session. Ship the fitted slope/intercept into the
per-device adapters once the sample count + correlation are solid.
"""
from __future__ import annotations
import bisect
import statistics
import time

from . import db

# best-available ground truth per metric (chest ECG for cardiac; ring optical for SpO2/temp until a reference oximeter exists)
REFERENCE = {"hr": "patch", "hrv": "patch", "spo2": "ring", "skin_temp": "ring"}


def _rows(metric: str, since: int) -> list[dict]:
    try:
        return db.rows("SELECT ts, value, source FROM vitals_ts WHERE metric = ? AND ts >= ? ORDER BY ts", (metric, since))
    except Exception:  # noqa: BLE001 — no vitals synced yet (table may not exist on a fresh DB)
        return []


def _pairs(rows: list[dict], ref_src: str, tol: int) -> tuple[dict[str, list[tuple[float, float]]], int]:
    """For each non-reference source, pair every sample with the nearest reference sample within ±tol seconds."""
    ref = sorted((r["ts"], r["value"]) for r in rows if r["source"] == ref_src)
    ref_ts = [t for t, _ in ref]
    others: dict[str, list[tuple[int, float]]] = {}
    for r in rows:
        if r["source"] == ref_src:
            continue
        others.setdefault(r["source"], []).append((r["ts"], r["value"]))
    out: dict[str, list[tuple[float, float]]] = {}
    for src, samples in others.items():
        pairs: list[tuple[float, float]] = []
        for ts, v in samples:
            i = bisect.bisect_left(ref_ts, ts)
            best = None
            for j in (i - 1, i):
                if 0 <= j < len(ref) and abs(ref[j][0] - ts) <= tol:
                    if best is None or abs(ref[j][0] - ts) < abs(ref[best][0] - ts):
                        best = j
            if best is not None:
                pairs.append((v, ref[best][1]))   # (device value, reference value)
        if pairs:
            out[src] = pairs
    return out, len(ref)


def _fit(pairs: list[tuple[float, float]]) -> dict | None:
    n = len(pairs)
    if n < 10:
        return None
    dev = [d for d, _ in pairs]
    ref = [x for _, x in pairs]
    bias = statistics.fmean(d - x for d, x in pairs)
    mae = statistics.fmean(abs(d - x) for d, x in pairs)
    rmse = statistics.fmean((d - x) ** 2 for d, x in pairs) ** 0.5
    mx, my = statistics.fmean(dev), statistics.fmean(ref)
    sx = sum((d - mx) ** 2 for d in dev)
    sy = sum((x - my) ** 2 for x in ref)
    sxy = sum((d - mx) * (x - my) for d, x in pairs)
    corr = sxy / (sx * sy) ** 0.5 if sx > 0 and sy > 0 else None
    slope = sxy / sx if sx > 0 else None                       # ref ≈ slope·device + intercept → correction toward truth
    intercept = my - slope * mx if slope is not None else None
    # agreement is "trusted" with enough samples and a strong correlation; otherwise "building"
    status = "trusted" if n >= 200 and corr is not None and corr >= 0.8 else "building"
    return {"n": n, "bias": round(bias, 2), "mae": round(mae, 2), "rmse": round(rmse, 2),
            "corr": round(corr, 3) if corr is not None else None,
            "correction": ({"slope": round(slope, 4), "intercept": round(intercept, 2)} if slope is not None else None),
            "status": status}


def report(metric: str = "hr", days: int = 7, tol_s: int = 10) -> dict:
    """Per-device calibration vs the reference for one metric over the last `days`. Device = value to correct,
    reference = truth; apply slope·device + intercept to correct toward the reference."""
    ref_src = REFERENCE.get(metric, "patch")
    since = int(time.time()) - max(1, days) * 86400
    rows = _rows(metric, since)
    if not rows:
        return {"metric": metric, "reference": ref_src, "devices": {}, "reference_samples": 0,
                "note": "No vitals for this metric yet — wear the devices so they sync."}
    pairs, ref_n = _pairs(rows, ref_src, tol_s)
    devices = {src: f for src, f in ((s, _fit(p)) for s, p in pairs.items()) if f}
    all_sources = sorted({r["source"] for r in rows})
    return {"metric": metric, "reference": ref_src, "reference_samples": ref_n, "tolerance_s": tol_s,
            "window_days": days, "sources_seen": all_sources, "devices": devices,
            "note": ("bias = mean(device − reference); apply correction slope·device + intercept to align a device to "
                     "the reference. Needs the reference ("+ref_src+") present and ≥10 overlapping samples per device; "
                     "marked 'trusted' at ≥200 samples and correlation ≥0.8.")}


def summary(days: int = 7) -> dict:
    """Calibration across the core metrics at once — the dashboard view."""
    return {"days": days, "metrics": {m: report(m, days) for m in ("hr", "hrv", "spo2", "skin_temp")}}
