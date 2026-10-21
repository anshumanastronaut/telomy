"""Calibration capture backend for the Telomy Recorder iPhone app.

Two jobs:
  • /cal/ingest  — the app streams time-aligned readings (patch, band, ring, WHOOP, reference) on one clock;
                   we store them so the workbench fit code (SpO2=c0−c1·ratio, °C=a·raw+b, HRV factor) can run on
                   real paired data.
  • /cal/whoop_latest — decode the last ~15 min of WHOOP raw already in the Vault into the values the app shows
                   on the same timeline (SpO2 red/IR ratio, skin-temp raw, HRV RMSSD, HR).

Bound to the WHOOP owner's Vault by the caller (TELOMY_WHOOP_USER_ID), same as /whoop/push. Read-mostly.
"""
from __future__ import annotations
import json
import math
import statistics as st

from . import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS cal_readings (
  session_id TEXT, source TEXT, channel TEXT, value REAL, t REAL, wall REAL, note TEXT
);
CREATE INDEX IF NOT EXISTS cal_readings_sess ON cal_readings (session_id, channel);
"""


def init():
    for stmt in SCHEMA.strip().split(";"):
        if stmt.strip():
            db.exec_(stmt)


def ingest(session_id: str, readings: list[dict]) -> int:
    init()
    n = 0
    for r in readings:
        try:
            db.exec_(
                "INSERT INTO cal_readings (session_id, source, channel, value, t, wall, note) VALUES (?,?,?,?,?,?,?)",
                (session_id, str(r.get("source")), str(r.get("channel")),
                 float(r.get("value")), float(r.get("t", 0)), float(r.get("wall", 0)), r.get("note")),
            )
            n += 1
        except (TypeError, ValueError):
            continue        # skip a malformed reading rather than failing the whole batch
    return n


def _win_rows(stream: str, t0: int, t1: int) -> list[dict]:
    return db.rows("SELECT key, data FROM whoop_rows WHERE stream=? AND ts BETWEEN ? AND ? ORDER BY ts", (stream, t0, t1))


def _clean_hrv(recs: list[tuple[int, float]]):
    """WHOOP over-delivers R-R ~2.4x. Collapse beats sharing a second (median), then Malik 20% filter → RMSSD."""
    byts: dict[int, list[float]] = {}
    for t, v in recs:
        if 300 <= v <= 2000:
            byts.setdefault(t, []).append(v)
    onep = [st.median(vs) for _, vs in sorted(byts.items())]
    if len(onep) < 2:
        return None, 0
    filt = [onep[0]]
    for v in onep[1:]:
        if abs(v - filt[-1]) / filt[-1] <= 0.20:
            filt.append(v)
    diffs = [(filt[i + 1] - filt[i]) ** 2 for i in range(len(filt) - 1)]
    return (math.sqrt(sum(diffs) / len(diffs)) if diffs else None), len(filt)


def whoop_latest(window_sec: int = 15 * 60) -> dict:
    """Decode the most recent WHOOP raw into the app's channels. Empty dict-ish if there's nothing recent."""
    init()
    tmaxrow = db.one("SELECT max(ts) AS m FROM whoop_rows WHERE stream='hrSample'")
    tmax = (tmaxrow or {}).get("m") or 0
    if not tmax:
        return {"live": {}, "note": "no WHOOP raw yet"}
    t0, t1 = tmax - window_sec, tmax
    live: dict = {}

    hr = [json.loads(r["data"]).get("bpm") for r in _win_rows("hrSample", t0, t1)]
    hr = [x for x in hr if x]
    if hr:
        live["hr"] = round(st.mean(hr), 1)

    sp = [json.loads(r["data"]) for r in _win_rows("spo2Sample", t0, t1)]
    red = [x["red"] for x in sp if x.get("red")]
    ir = [x["ir"] for x in sp if x.get("ir")]
    if red and ir:
        live["red"] = round(st.mean(red), 1)
        live["ir"] = round(st.mean(ir), 1)
        live["spo2_ratio"] = round(st.mean(red) / st.mean(ir), 4)

    tp = [json.loads(r["data"]).get("raw") for r in _win_rows("skinTempSample", t0, t1)]
    tp = [x for x in tp if x is not None]
    if tp:
        live["temp_raw"] = round(st.mean(tp), 1)

    rr = []
    for r in _win_rows("rrInterval", t0, t1):
        try:
            k = json.loads(r["key"])
            rr.append((int(k["ts"]), float(k["rrMs"])))
        except (KeyError, ValueError, TypeError):
            continue
    rmssd, beats = _clean_hrv(rr)
    if rmssd:
        live["hrv_rmssd"] = round(rmssd, 1)
        live["hrv_beats"] = beats

    return {"live": live, "t0": t0, "t1": t1}
