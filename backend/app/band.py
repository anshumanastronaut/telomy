"""ECG band data: minute summaries from the live stream, saved ECG strips and synced on-device recordings.

The phone does the signal processing (QRS detection, signal quality, Lipponen–Tarvainen artefact correction, Task Force
time-domain HRV; see mobile/modules/ky-ecg). The server stores what the phone computed plus raw samples for strips, so
the analysis can be re-run later. Every table carries `user_id` (production plan, phase 1).
"""
from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS band_minutes (
  user_id INTEGER NOT NULL DEFAULT 1, ts TEXT NOT NULL, hr REAL, rmssd REAL, sdnn REAL, beats INTEGER,
  quality TEXT, artefact_pct REAL, source TEXT, PRIMARY KEY (user_id, ts));
CREATE TABLE IF NOT EXISTS ecg_strips (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 1, ts TEXT NOT NULL, fs REAL NOT NULL,
  duration_s REAL, hr REAL, rmssd REAL, quality TEXT, samples TEXT NOT NULL, note TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS band_recordings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 1, start_ts TEXT NOT NULL, duration_s REAL,
  beats INTEGER, mean_hr REAL, rmssd REAL, sdnn REAL, artefact_pct REAL, rr TEXT, source TEXT, sleep TEXT,
  UNIQUE (user_id, start_ts));
CREATE TABLE IF NOT EXISTS band_captures (
  id TEXT NOT NULL, user_id INTEGER NOT NULL DEFAULT 1, therapy TEXT, started_at TEXT, duration_s REAL, meta TEXT, bundle TEXT,
  received_at TEXT, PRIMARY KEY (user_id, id));
CREATE TABLE IF NOT EXISTS band_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 1, type TEXT NOT NULL, start_ts TEXT NOT NULL,
  end_ts TEXT NOT NULL, detail TEXT, source TEXT, UNIQUE (user_id, type, start_ts));
"""

SOURCE = "KY-E-B1 ECG band"
QUALITIES = {"good", "acceptable", "poor", "no_contact", "warming_up"}


EVENT_TYPES = {
    "af_pattern": ("Irregular rhythm pattern (possible AF)", "high"),
    "pause": ("Pause between beats over 2 s", "high"),
    "bradycardia": ("Slow heart rate", "medium"),
    "tachycardia_rest": ("Fast heart rate at rest", "medium"),
    "very_high_hr": ("Very fast heart rate", "high"),
    "early_beats": ("Frequent early beats", "low"),
    "bigeminy": ("Early beat every second beat", "medium"),
    "trigeminy": ("Early beat every third beat", "low"),
    "poor_signal": ("Long stretch of poor signal", "info"),
}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)
        cols = [r[1] for r in c.execute("PRAGMA table_info(band_recordings)")]
        if "sleep" not in cols:  # databases created before sleep analysis
            c.execute("ALTER TABLE band_recordings ADD COLUMN sleep TEXT")


def _check(v, lo, hi, name):
    if v is None:
        return None
    v = float(v)
    if not lo <= v <= hi:
        raise ValueError(f"{name} {v:g} is outside the plausible range {lo}–{hi}")
    return round(v, 2)


def save_minutes(items: list[dict], user_id: int = 1) -> dict:
    """Upsert per-minute summaries [{ts, hr, rmssd, sdnn, beats, quality, artefact_pct}]."""
    if len(items) > 1440:
        raise ValueError("Send at most one day of minutes per request")
    n = 0
    with db.tx() as c:
        for it in items:
            ts = str(it["ts"])[:16]
            q = it.get("quality") if it.get("quality") in QUALITIES else None
            c.execute("INSERT OR REPLACE INTO band_minutes (user_id, ts, hr, rmssd, sdnn, beats, quality, artefact_pct, source) "
                      "VALUES (?,?,?,?,?,?,?,?,?)",
                      (user_id, ts, _check(it.get("hr"), 25, 250, "Heart rate"), _check(it.get("rmssd"), 0, 400, "RMSSD"),
                       _check(it.get("sdnn"), 0, 400, "SDNN"), int(it.get("beats") or 0), q,
                       _check(it.get("artefact_pct"), 0, 100, "Artefact %"), SOURCE))
            n += 1
    return {"saved": n}


def minutes(hours: int = 24, user_id: int = 1) -> list[dict]:
    hours = max(1, min(hours, 24 * 14))
    return db.rows(f"SELECT ts, hr, rmssd, sdnn, beats, quality, artefact_pct FROM band_minutes WHERE user_id = ? "
                   f"AND ts >= strftime('%Y-%m-%dT%H:%M', datetime(?, '-{hours} hours')) ORDER BY ts",
                   (user_id, engine.now_iso()))


def summary(user_id: int = 1) -> dict:
    rows = minutes(24, user_id)
    hr = [r["hr"] for r in rows if r["hr"] and r["quality"] in ("good", "acceptable")]
    rm = [r["rmssd"] for r in rows if r["rmssd"] and r["quality"] in ("good", "acceptable")]
    last = rows[-1] if rows else None
    return {"minutes": len(rows), "last": last,
            "hr": {"min": min(hr), "avg": round(sum(hr) / len(hr), 1), "max": max(hr)} if hr else None,
            "rmssd": {"median": sorted(rm)[len(rm) // 2]} if rm else None,
            "strips": db.one("SELECT COUNT(*) AS n FROM ecg_strips WHERE user_id = ?", (user_id,))["n"],
            "recordings": db.one("SELECT COUNT(*) AS n FROM band_recordings WHERE user_id = ?", (user_id,))["n"],
            "source": SOURCE}


def save_strip(body: dict, user_id: int = 1) -> dict:
    fs = _check(body.get("fs"), 50, 1000, "Sampling rate")
    samples = body.get("samples") or []
    if not fs or len(samples) < fs * 5:
        raise ValueError("An ECG strip needs at least 5 seconds of samples")
    if len(samples) > fs * 120:
        raise ValueError("ECG strips are limited to 2 minutes")
    samples = [round(float(s), 1) for s in samples]
    sid = db.exec_("INSERT INTO ecg_strips (user_id, ts, fs, duration_s, hr, rmssd, quality, samples, note, source) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (user_id, body.get("ts") or engine.now_iso(), fs, round(len(samples) / fs, 2),
                    _check(body.get("hr"), 25, 250, "Heart rate"), _check(body.get("rmssd"), 0, 400, "RMSSD"),
                    body.get("quality") if body.get("quality") in QUALITIES else None, db.j(samples),
                    (body.get("note") or "")[:500], SOURCE))
    return strip(sid, user_id)


def strips(user_id: int = 1) -> list[dict]:
    return db.rows("SELECT id, ts, fs, duration_s, hr, rmssd, quality, note FROM ecg_strips WHERE user_id = ? ORDER BY ts DESC", (user_id,))


def strip(sid: int, user_id: int = 1) -> dict | None:
    r = db.one("SELECT * FROM ecg_strips WHERE id = ? AND user_id = ?", (sid, user_id))
    if r:
        r["samples"] = db.unj(r["samples"], [])
    return r


def save_recording(body: dict, user_id: int = 1) -> dict:
    rr = [float(x) for x in (body.get("rr") or [])][:200_000]
    db.exec_("INSERT OR REPLACE INTO band_recordings (user_id, start_ts, duration_s, beats, mean_hr, rmssd, sdnn, artefact_pct, rr, source, sleep) "
             "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
             (user_id, str(body["start_ts"])[:19], _check(body.get("duration_s"), 0, 7 * 86400, "Duration"),
              int(body.get("beats") or 0), _check(body.get("mean_hr"), 25, 250, "Heart rate"),
              _check(body.get("rmssd"), 0, 400, "RMSSD"), _check(body.get("sdnn"), 0, 400, "SDNN"),
              _check(body.get("artefact_pct"), 0, 100, "Artefact %"), db.j(rr), SOURCE,
              db.j(body["sleep"]) if isinstance(body.get("sleep"), dict) else None))
    r = db.one("SELECT id, start_ts, duration_s, beats, mean_hr, rmssd, sdnn, artefact_pct, sleep FROM band_recordings "
               "WHERE user_id = ? AND start_ts = ?", (user_id, str(body["start_ts"])[:19]))
    r["sleep"] = db.unj(r["sleep"], None)
    return r


def recordings(user_id: int = 1) -> list[dict]:
    rows = db.rows("SELECT id, start_ts, duration_s, beats, mean_hr, rmssd, sdnn, artefact_pct, sleep FROM band_recordings "
                   "WHERE user_id = ? ORDER BY start_ts DESC", (user_id,))
    for r in rows:
        r["sleep"] = db.unj(r["sleep"], None)
    return rows


def _iso(t) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(float(t)).isoformat(timespec="seconds") if isinstance(t, (int, float)) else str(t)[:19]


def save_events(items: list[dict], user_id: int = 1) -> dict:
    """Upsert rhythm/signal events; an episode is identified by (type, start) and its end is extended on updates."""
    n = 0
    with db.tx() as c:
        for e in items[:500]:
            if e.get("type") not in EVENT_TYPES:
                raise ValueError(f"Unknown event type {e.get('type')!r}")
            c.execute("INSERT INTO band_events (user_id, type, start_ts, end_ts, detail, source) VALUES (?,?,?,?,?,?) "
                      "ON CONFLICT (user_id, type, start_ts) DO UPDATE SET end_ts = excluded.end_ts, detail = excluded.detail",
                      (user_id, e["type"], _iso(e["start"]), _iso(e.get("end", e["start"])), db.j(e.get("detail") or {}),
                       e.get("source") or "live"))
            n += 1
    return {"saved": n}


def events(days: int = 30, user_id: int = 1) -> list[dict]:
    rows = db.rows("SELECT id, type, start_ts, end_ts, detail, source FROM band_events WHERE user_id = ? "
                   "AND start_ts >= date(?, ?) ORDER BY start_ts DESC", (user_id, engine.now_iso()[:10], f"-{max(1, days)} days"))
    for r in rows:
        r["detail"] = db.unj(r["detail"], {})
        r["label"], r["severity"] = EVENT_TYPES[r["type"]]
    return rows


def save_capture(bundle: dict, user_id: int = 1) -> dict:
    """Store a therapy capture exported by the phone (format telomy.capture/1), as-is, for research and re-analysis."""
    if bundle.get("format") != "telomy.capture/1":
        raise ValueError("Not a Telomy capture (expected format telomy.capture/1)")
    meta = bundle.get("meta") or {}
    if not meta.get("id"):
        raise ValueError("Capture has no id")
    db.exec_("INSERT OR REPLACE INTO band_captures (id, user_id, therapy, started_at, duration_s, meta, bundle, received_at) VALUES (?,?,?,?,?,?,?,?)",
             (meta["id"], user_id, meta.get("therapy"), _iso(meta.get("startedAt", 0)), meta.get("durationSec"), db.j(meta), db.j(bundle), engine.now_iso()))
    return {"id": meta["id"], "stored": True}


def captures(user_id: int = 1) -> list[dict]:
    rows = db.rows("SELECT id, therapy, started_at, duration_s, meta, received_at FROM band_captures WHERE user_id = ? ORDER BY started_at DESC", (user_id,))
    for r in rows:
        m = db.unj(r.pop("meta"), {})
        r.update({k: m.get(k) for k in ("settings", "phases", "pre", "post", "notes", "summary")})
    return rows


def capture_bundle(cid: str, user_id: int = 1) -> dict | None:
    r = db.one("SELECT bundle FROM band_captures WHERE id = ? AND user_id = ?", (cid, user_id))
    return db.unj(r["bundle"], None) if r else None
