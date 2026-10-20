"""CGM via a Nightscout-compatible receiver — open-source CGM readers (Juggluco on Android, xDrip+/xDrip4iOS) upload
sensor glucose (FreeStyle Libre 2/3, Dexcom G7, Sibionics …) to a "Nightscout URL"; Telomy *is* that URL:
  https://<server>/nightscout   with the API secret in TELOMY_NIGHTSCOUT_SECRET.
Implements the subset uploaders use: GET /api/v1/status.json, POST/GET /api/v1/entries(.json) with the `api-secret`
header (SHA-1 of the secret, Nightscout convention) or `?token=`. Readings stay on the user's server.
Analytics (International Consensus on Time in Range, Battelino 2019): mean, GMI (Bergenstal 2018: 3.31 + 0.02392 × mean
mg/dL), time in range 70–180, below 70 / 54, above 180 / 250, CV (stable < 36 %); daily mean → signals.glucose_mean.
"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from . import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS cgm_readings (ts INTEGER PRIMARY KEY, mgdl REAL, direction TEXT, device TEXT, source TEXT);
"""
IST = timezone(timedelta(hours=5, minutes=30))


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def secret_ok(api_secret: str | None, token: str | None) -> bool:
    s = os.environ.get("TELOMY_NIGHTSCOUT_SECRET", "")
    if not s:
        return False
    sha = hashlib.sha1(s.encode()).hexdigest()
    return any(x and (hmac.compare_digest(x.lower(), sha) or hmac.compare_digest(x, s)) for x in (api_secret, token))


def status() -> dict:
    return {"status": "ok", "name": "Telomy", "version": "15.0.0-telomy", "serverTime": datetime.now(timezone.utc).isoformat(),
            "apiEnabled": True, "careportalEnabled": False, "settings": {"units": "mg/dl"}}


def add_entries(items: list[dict]) -> int:
    rows = []
    for e in items if isinstance(items, list) else [items]:
        if not isinstance(e, dict) or e.get("type", "sgv") != "sgv":
            continue
        v = e.get("sgv") or e.get("mgdl")
        t = e.get("date") or e.get("mills")
        if t is None and e.get("dateString"):
            try:
                t = datetime.fromisoformat(str(e["dateString"]).replace("Z", "+00:00")).timestamp() * 1000
            except ValueError:
                t = None
        try:
            v, t = float(v), int(float(t) / 1000)
        except (TypeError, ValueError):
            continue
        if not (20 <= v <= 600) or t < 1_577_836_800:
            continue
        rows.append((t, v, e.get("direction"), e.get("device"), "nightscout"))
    with db.tx() as c:
        c.executemany("INSERT OR REPLACE INTO cgm_readings VALUES (?,?,?,?,?)", rows)
    _daily_means({datetime.fromtimestamp(t, IST).date().isoformat() for t, *_ in rows})
    return len(rows)


def _daily_means(days: set[str]):
    for d in days:
        a = int(datetime.fromisoformat(d).replace(tzinfo=IST).timestamp())
        v = [r["mgdl"] for r in db.rows("SELECT mgdl FROM cgm_readings WHERE ts >= ? AND ts < ?", (a, a + 86400))]
        if len(v) >= 48:                                   # ≥ 4 h of 5-min readings before a daily mean means anything
            db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (d, "glucose_mean", round(sum(v) / len(v), 1), "CGM"))


def entries(count: int = 100) -> list[dict]:
    return [{"type": "sgv", "sgv": r["mgdl"], "date": r["ts"] * 1000, "direction": r["direction"], "device": r["device"]}
            for r in db.rows("SELECT * FROM cgm_readings ORDER BY ts DESC LIMIT ?", (max(1, min(count, 2000)),))]


def summary(days: int = 14) -> dict:
    since = int(datetime.now(timezone.utc).timestamp()) - days * 86400
    v = [r["mgdl"] for r in db.rows("SELECT mgdl FROM cgm_readings WHERE ts >= ?", (since,))]
    if len(v) < 288:                                       # < 1 day of readings
        return {"ok": False, "readings": len(v), "reason": "Needs at least a day of CGM readings."}
    n = len(v); m = sum(v) / n
    sd = (sum((x - m) ** 2 for x in v) / (n - 1)) ** 0.5
    pct = lambda f: round(100 * sum(1 for x in v if f(x)) / n, 1)  # noqa: E731
    return {"ok": True, "days": days, "readings": n, "mean": round(m), "gmi": round(3.31 + 0.02392 * m, 1), "cv": round(100 * sd / m, 1),
            "tir": pct(lambda x: 70 <= x <= 180), "tbr70": pct(lambda x: x < 70), "tbr54": pct(lambda x: x < 54),
            "tar180": pct(lambda x: x > 180), "tar250": pct(lambda x: x > 250),
            "targets": "TIR > 70 %, below 70 < 4 %, below 54 < 1 %, above 180 < 25 %, CV ≤ 36 % (International Consensus 2019)"}
