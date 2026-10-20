"""Longitudinal vitals — one high-frequency timeline every device syncs into, so the whole day's physiology is on a
single clock and can be correlated with events, therapies, movement and sleep by timestamp.

Design (matching how the devices actually sample):
  * The patch (ECG), the ring and WHOOP each store continuously on-device at their native cadence and sync in batches
    (smart sync: Wi-Fi/charging preferred, small deltas often, a full backfill when a gap is detected). The phone posts
    those batches here.
  * Cadence is adaptive, recorded per sample as `step_s`: ~5-10 s at rest (a summary value per window), 1 s (1 Hz) for a
    live view, and continuous 1 Hz while a therapy/workout session is open. Nothing is lost — gaps are real "no data".
  * Storage is one tall table keyed (ts, metric, source); INSERT OR REPLACE makes re-sync idempotent. Reads downsample
    to the requested resolution so a day of 1 Hz data renders fast.

This is the store and the sync contract; the always-on native capture on the patch/ring is the device-side half.
"""
from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS vitals_ts (
  ts INTEGER, metric TEXT, value REAL, source TEXT, step_s INTEGER DEFAULT 1,
  PRIMARY KEY (ts, metric, source));
CREATE INDEX IF NOT EXISTS ix_vitals_metric_ts ON vitals_ts(metric, ts);
"""
# metrics the timeline understands (others are accepted but not summarised)
METRICS = {"hr": "Heart rate", "hrv": "HRV (RMSSD)", "spo2": "Blood oxygen", "skin_temp": "Skin temperature",
           "resp": "Breathing rate", "steps": "Steps", "motion": "Movement", "stress": "Stress", "ecg_quality": "ECG quality"}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def ingest(samples: list[dict], source: str) -> dict:
    """A batch of {ts, metric, value, step_s?} from a device. Idempotent (re-syncing the same window is safe)."""
    rows, lo, hi = [], None, None
    for s in samples:
        try:
            ts = int(s["ts"]); v = float(s["value"]); m = str(s["metric"])
        except (KeyError, TypeError, ValueError):
            continue
        if ts < 1_577_836_800 or ts > 4_102_444_800:        # 2020..2100 sanity
            continue
        rows.append((ts, m, v, source, int(s.get("step_s", 1))))
        lo = ts if lo is None else min(lo, ts)
        hi = ts if hi is None else max(hi, ts)
    if rows:
        with db.tx() as c:
            c.executemany("INSERT OR REPLACE INTO vitals_ts (ts, metric, value, source, step_s) VALUES (?,?,?,?,?)", rows)
    return {"stored": len(rows), "from": lo, "to": hi}


def series(metric: str, start: int, end: int, max_points: int = 1000) -> dict:
    """Downsampled series for display: mean per bucket so a day of 1 Hz data returns ~max_points."""
    rows = db.rows("SELECT ts, value, source, step_s FROM vitals_ts WHERE metric = ? AND ts >= ? AND ts <= ? ORDER BY ts",
                   (metric, start, end))
    if not rows:
        return {"metric": metric, "points": [], "n": 0, "coverage_s": 0}
    span = max(1, end - start)
    bucket = max(1, span // max_points)
    agg: dict[int, list[float]] = {}
    covered = 0
    for r in rows:
        agg.setdefault((r["ts"] // bucket) * bucket, []).append(r["value"])
        covered += r["step_s"] or 1
    pts = [[b, round(sum(v) / len(v), 2)] for b, v in sorted(agg.items())]
    sources = sorted({r["source"] for r in rows})
    return {"metric": metric, "label": METRICS.get(metric, metric), "points": pts, "n": len(rows),
            "bucket_s": bucket, "coverage_s": covered, "sources": sources}


def day(day_iso: str | None = None) -> dict:
    """A day's vitals timeline aligned with what happened — events, therapies, meals, the night — on one clock, so any
    window can be correlated (e.g. HR during a sauna, HRV around a late meal)."""
    from datetime import datetime, timedelta, timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    d = datetime.fromisoformat(day_iso) if day_iso else datetime.now(ist)
    start = int(datetime(d.year, d.month, d.day, tzinfo=ist).timestamp())
    end = start + 86400
    metrics = {m: series(m, start, end, 500) for m in ("hr", "hrv", "spo2", "skin_temp", "resp", "motion", "steps")}
    metrics = {m: s for m, s in metrics.items() if s["n"]}
    if "hr" not in metrics:                               # until the patch/ring has synced, show WHOOP's 1 Hz HR so the day isn't empty
        wh = _whoop_hr(start, end)
        if wh["n"]:
            metrics["hr"] = wh
    ev = db.rows("SELECT ts, kind, label FROM events WHERE ts >= ? AND ts <= ? ORDER BY ts",
                 (datetime.fromtimestamp(start, ist).isoformat(), datetime.fromtimestamp(end, ist).isoformat()))
    overlay = [{"ts": e["ts"], "kind": e["kind"], "label": e["label"]} for e in ev]
    total = sum(s["coverage_s"] for s in metrics.values())
    return {"day": d.date().isoformat(), "start": start, "end": end, "metrics": metrics, "events": overlay,
            "coverage_hours": round(total / 3600 / max(1, len(metrics)), 1) if metrics else 0,
            "note": "One clock for the whole day — vitals, events, therapies and sleep share timestamps, so any window correlates."}


def coverage(days: int = 7) -> dict:
    """How complete the longitudinal record is — hours of vitals captured per day, per source (the goal is all-day)."""
    import time
    now = int(time.time())
    rows = db.rows("SELECT source, COUNT(*) AS n, SUM(step_s) AS secs, MIN(ts) AS lo, MAX(ts) AS hi FROM vitals_ts WHERE ts >= ? GROUP BY source",
                   (now - days * 86400,))
    return {"days": days, "by_source": [{"source": r["source"], "samples": r["n"], "hours": round((r["secs"] or 0) / 3600, 1),
                                         "from": r["lo"], "to": r["hi"]} for r in rows],
            "goal": "Continuous all-day capture from the patch, ring and WHOOP, synced smartly."}


def _whoop_hr(start: int, end: int, max_points: int = 500) -> dict:
    """WHOOP 1 Hz heart rate for the day (from whoop_rows), downsampled — a fallback so the timeline has data before
    the patch/ring sync into vitals_ts."""
    import json as _j
    try:
        rows = db.rows("SELECT ts, data FROM whoop_rows WHERE stream='hrSample' AND ts >= ? AND ts < ? ORDER BY ts", (start, end))
    except Exception:  # noqa: BLE001
        return {"metric": "hr", "points": [], "n": 0, "coverage_s": 0}
    if not rows:
        return {"metric": "hr", "points": [], "n": 0, "coverage_s": 0}
    bucket = max(1, (end - start) // max_points)
    agg: dict[int, list[float]] = {}
    for r in rows:
        b = _j.loads(r["data"]).get("bpm")
        if b and 25 <= b <= 220:
            agg.setdefault((r["ts"] // bucket) * bucket, []).append(b)
    pts = [[b, round(sum(v) / len(v))] for b, v in sorted(agg.items())]
    return {"metric": "hr", "label": "Heart rate", "points": pts, "n": len(rows), "bucket_s": bucket,
            "coverage_s": len(rows), "sources": ["WHOOP"]}
