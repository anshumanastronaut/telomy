"""Centre machine telemetry: cryo chambers, hyperbaric chambers, saunas, PBM beds, PEMF beds, compression, plunges…

Each machine streams its *control* channels (what it did to the body: chamber temperature, pressure, O₂ %, irradiance,
field strength…) to the Telomy server, authenticated with a per-device key — directly over HTTPS or via the MQTT bridge
(tools/mqtt_bridge.py). Telomy then:
  1. links telemetry to the person's session on that device (same device, overlapping time window);
  2. computes the dose actually delivered vs the prescription ("−152 °C for 168 s; prescribed −140 °C for 180 s");
  3. raises machine alarms (out-of-range pressure, PEMF coil > 45 °C, sauna > 100 °C, O₂ below prescription…);
  4. drives the person's physiology prior with the *measured* machine inputs instead of the prescribed ones.
Body signals come separately from the wearable / Telomy patch via /therapy/sessions/{id}/samples (see docs/DEVICE_INTEGRATION.md).
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS device_keys (device_id TEXT PRIMARY KEY, key_hash TEXT, created_at TEXT, last_seen TEXT);
CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT, ts TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS ix_telemetry_device_ts ON telemetry(device_id, ts);
"""

# channel: (label, unit, lo, hi) — hard limits outside which the machine raises an alarm
CHANNELS = {
    "cryo": {"chamber_temp_c": ("Chamber temperature", "°C", -185, -60), "door_open": ("Door open", "", 0, 1)},
    "cryo_local": {"nozzle_temp_c": ("Nozzle temperature", "°C", -170, 0)},
    "cold": {"water_temp_c": ("Water temperature", "°C", 1, 16)},
    "sauna": {"temp_c": ("Cabin temperature", "°C", 20, 100), "humidity_pct": ("Humidity", "%", 0, 60)},
    "sauna_ir": {"temp_c": ("Cabin temperature", "°C", 20, 75), "panel_power_pct": ("Panel power", "%", 0, 100)},
    "contrast": {"temp_c": ("Sauna temperature", "°C", 20, 100), "water_temp_c": ("Plunge temperature", "°C", 1, 16)},
    "hbot": {"pressure_ata": ("Pressure", "ATA", 0.95, 2.5), "o2_pct": ("Oxygen", "%", 19, 100), "chamber_temp_c": ("Chamber temperature", "°C", 15, 30),
             "co2_ppm": ("CO₂", "ppm", 0, 5000), "humidity_pct": ("Humidity", "%", 0, 80)},
    "hbot_mild": {"pressure_ata": ("Pressure", "ATA", 0.95, 1.55), "o2_pct": ("Oxygen at mask", "%", 19, 96), "chamber_temp_c": ("Chamber temperature", "°C", 15, 30)},
    "redlight": {"irradiance_mw_cm2": ("Irradiance", "mW/cm²", 0, 120), "panel_temp_c": ("Panel temperature", "°C", 15, 45)},
    "pemf": {"field_gauss": ("Field strength", "G", 0, 60), "frequency_hz": ("Frequency", "Hz", 0, 100), "coil_temp_c": ("Coil temperature", "°C", 15, 45)},
    "halo": {"field_gauss": ("PEMF field", "G", 0, 60), "irradiance_mw_cm2": ("PBM irradiance", "mW/cm²", 0, 100), "coil_temp_c": ("Coil temperature", "°C", 15, 45),
             "bed_temp_c": ("FIR bed temperature", "°C", 15, 42)},
    "compression": {"pressure_mmhg": ("Cuff pressure", "mmHg", 0, 120)},
    "vibroacoustic": {"frequency_hz": ("Frequency", "Hz", 20, 150), "amplitude_pct": ("Amplitude", "%", 0, 100)},
    "h2_inhal": {"h2_pct": ("H₂ concentration", "%", 0, 4), "flow_ml_min": ("Flow", "mL/min", 0, 1500)},
    "ihht": {"fio2_pct": ("Inspired O₂", "%", 9, 40)},
    "ewot": {"o2_lpm": ("O₂ flow", "L/min", 0, 15), "power_w": ("Bike power", "W", 0, 600)},
    "float": {"water_temp_c": ("Water temperature", "°C", 33, 37)},
    "iv": {"rate_ml_h": ("Infusion rate", "mL/h", 0, 1500), "volume_ml": ("Volume infused", "mL", 0, 1000)},
    "wbv": {"frequency_hz": ("Frequency", "Hz", 0, 50)},
}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def issue_key(device_id: str) -> dict:
    if not db.one("SELECT id FROM devices WHERE id = ?", (device_id,)):
        raise LookupError("Unknown device")
    key = "tdk_" + secrets.token_urlsafe(24)
    db.exec_("INSERT OR REPLACE INTO device_keys (device_id, key_hash, created_at, last_seen) VALUES (?,?,?,NULL)",
             (device_id, _hash(key), engine.now_iso()))
    return {"device_id": device_id, "key": key, "note": "Shown once. Store it in the machine's gateway config; rotate by issuing a new one."}


def _check(device_id: str, key: str | None) -> dict:
    dev = db.one("SELECT * FROM devices WHERE id = ?", (device_id,))
    if not dev:
        raise LookupError("Unknown device")
    k = db.one("SELECT key_hash FROM device_keys WHERE device_id = ?", (device_id,))
    if not k or not key or not secrets.compare_digest(k["key_hash"], _hash(key)):
        raise PermissionError("Invalid device key")
    return dev


def ingest(device_id: str, key: str | None, samples: list[dict]) -> dict:
    """samples: [{"ts": ISO-8601, <channel>: number, ..., "status": "ok"|"<error code>"}] — 1–10 s resolution recommended."""
    dev = _check(device_id, key)
    chans = CHANNELS.get(dev["modality"], {})
    if not samples:
        raise ValueError("No samples")
    if len(samples) > 20000:
        raise ValueError("Too many samples in one request (max 20,000) — batch them.")
    alarms, stored = [], 0
    for s in samples:
        ts = s.get("ts")
        try:
            datetime.fromisoformat(ts)
        except (TypeError, ValueError):
            raise ValueError(f"Bad timestamp: {ts!r}")
        data = {}
        for k, v in s.items():
            if k == "ts":
                continue
            if k == "status":
                data[k] = str(v)[:40]
                if str(v).lower() not in ("ok", "running", "idle"):
                    alarms.append({"ts": ts, "channel": "status", "value": v, "message": f"Machine reported {v}"})
                continue
            if k not in chans:
                continue  # unknown channels are ignored, never stored
            if not isinstance(v, (int, float)):
                raise ValueError(f"{k} must be numeric")
            data[k] = float(v)
            lo, hi = chans[k][2], chans[k][3]
            if not lo <= v <= hi:
                alarms.append({"ts": ts, "channel": k, "value": v, "message": f"{chans[k][0]} {v} {chans[k][1]} outside {lo}–{hi}"})
        db.exec_("INSERT INTO telemetry (device_id, ts, data) VALUES (?,?,?)", (device_id, ts[:19], db.j(data)))
        stored += 1
    db.exec_("UPDATE device_keys SET last_seen = ? WHERE device_id = ?", (engine.now_iso(), device_id))
    if alarms:
        db.exec_("UPDATE devices SET telemetry = ? WHERE id = ?", (db.j({"last_alarm": alarms[-1]}), device_id))
    return {"device_id": device_id, "stored": stored, "alarms": alarms[:20]}


def series(device_id: str, start: str, end: str) -> list[dict]:
    rows = db.rows("SELECT ts, data FROM telemetry WHERE device_id = ? AND ts BETWEEN ? AND ? ORDER BY ts", (device_id, start[:19], end[:19]))
    return [{"ts": r["ts"], **db.unj(r["data"], {})} for r in rows]


def recent(device_id: str, minutes: int = 120) -> dict:
    dev = db.one("SELECT * FROM devices WHERE id = ?", (device_id,))
    if not dev:
        raise LookupError("Unknown device")
    end = datetime.fromisoformat(engine.now_iso())
    last = db.one("SELECT MAX(ts) AS t FROM telemetry WHERE device_id = ?", (device_id,))["t"]
    if last and datetime.fromisoformat(last) < end - timedelta(minutes=minutes):
        end = datetime.fromisoformat(last)  # show the latest run even if it was earlier
    rows = series(device_id, (end - timedelta(minutes=minutes)).isoformat(), end.isoformat())
    k = db.one("SELECT created_at, last_seen FROM device_keys WHERE device_id = ?", (device_id,))
    return {"device": dev, "channels": {c: {"label": v[0], "unit": v[1], "limits": [v[2], v[3]]} for c, v in CHANNELS.get(dev["modality"], {}).items()},
            "samples": rows, "connected": bool(k), "last_seen": (k or {}).get("last_seen")}


def for_session(sess: dict) -> dict | None:
    """Telemetry overlapping a therapy session on the same device, and the delivered dose vs prescription."""
    if not sess.get("device_id"):
        return None
    t0 = datetime.fromisoformat(sess["ts"]) - timedelta(minutes=10)
    t1 = datetime.fromisoformat(sess["ts"]) + timedelta(minutes=(sess.get("minutes") or 30) + 40)
    rows = series(sess["device_id"], t0.isoformat(), t1.isoformat())
    if len(rows) < 3:
        return None
    mod = sess["modality"]
    p = sess.get("params") or {}
    step = max(1.0, (datetime.fromisoformat(rows[-1]["ts"]) - datetime.fromisoformat(rows[0]["ts"])).total_seconds() / max(1, len(rows) - 1))
    vals = lambda k: [r[k] for r in rows if k in r]  # noqa: E731
    d: dict = {"samples": len(rows), "resolution_s": round(step, 1)}
    checks = []
    if mod in ("cryo",):
        t = vals("chamber_temp_c")
        active = [x for x in t if x <= -90]
        d.update({"min_temp_c": min(t), "mean_active_temp_c": round(sum(active) / len(active), 1) if active else None,
                  "seconds_below_minus110": round(sum(1 for x in t if x <= -110) * step), "measured_chamber_c": round(sum(active) / len(active)) if active else None})
        if p.get("chamber_c") and d["mean_active_temp_c"] is not None:
            checks.append(("Chamber temperature", p["chamber_c"], d["mean_active_temp_c"], "°C", 10))
        if p.get("seconds"):
            checks.append(("Exposure", p["seconds"], round(len(active) * step), "s", 30))
    elif mod in ("hbot", "hbot_mild"):
        a = vals("pressure_ata")
        o = vals("o2_pct")
        top = max(a)
        at = [x for x in a if x >= top - 0.05]
        d.update({"max_ata": round(top, 2), "minutes_at_pressure": round(len(at) * step / 60, 1), "mean_o2_pct": round(sum(o) / len(o), 1) if o else None,
                  "compression_min": round(next((i for i, x in enumerate(a) if x >= top - 0.05), 0) * step / 60, 1), "measured_ata": round(top, 2)})
        if p.get("ata"):
            checks.append(("Pressure", p["ata"], d["max_ata"], "ATA", 0.1))
        if p.get("o2_pct") and o:
            checks.append(("Oxygen", p["o2_pct"], d["mean_o2_pct"], "%", 5))
        if p.get("minutes"):
            checks.append(("Time at pressure", p["minutes"] - 20, d["minutes_at_pressure"], "min", 8))
    elif mod in ("sauna", "sauna_ir", "contrast"):
        t = vals("temp_c")
        hot = [x for x in t if x >= (60 if mod != "sauna_ir" else 40)]
        d.update({"mean_temp_c": round(sum(hot) / len(hot), 1) if hot else None, "minutes_hot": round(len(hot) * step / 60, 1), "max_temp_c": max(t),
                  "measured_temp_c": round(sum(hot) / len(hot)) if hot else None})
        if p.get("temp_c") and hot:
            checks.append(("Temperature", p["temp_c"], d["mean_temp_c"], "°C", 6))
    elif mod in ("redlight", "halo"):
        irr = vals("irradiance_mw_cm2")
        d.update({"delivered_j_cm2": round(sum(irr) * step / 1000, 1), "mean_irradiance": round(sum(irr) / len(irr), 1) if irr else None})
        if p.get("irradiance_mw_cm2") and p.get("minutes"):
            checks.append(("Light dose", round(p["irradiance_mw_cm2"] * p["minutes"] * 60 / 1000, 1), d["delivered_j_cm2"], "J/cm²", 10))
    elif mod == "pemf":
        g = vals("field_gauss")
        on = [x for x in g if x > 1]
        d.update({"mean_gauss": round(sum(on) / len(on), 1) if on else 0, "minutes_on": round(len(on) * step / 60, 1), "max_coil_temp_c": max(vals("coil_temp_c") or [0])})
        if p.get("intensity_gauss"):
            checks.append(("Field strength", p["intensity_gauss"], d["mean_gauss"], "G", 4))
    elif mod in ("cold", "float"):
        w = vals("water_temp_c")
        d.update({"mean_water_temp_c": round(sum(w) / len(w), 1) if w else None})
        if p.get("water_c") and w:
            checks.append(("Water temperature", p["water_c"], d["mean_water_temp_c"], "°C", 2))
    elif mod == "compression":
        m = vals("pressure_mmhg")
        d.update({"mean_mmhg": round(sum(x for x in m if x > 5) / max(1, len([x for x in m if x > 5])), 1)})
        if p.get("pressure_mmhg"):
            checks.append(("Cuff pressure", p["pressure_mmhg"], d["mean_mmhg"], "mmHg", 15))
    d["vs_prescribed"] = [{"what": w, "prescribed": a, "delivered": b, "unit": u, "ok": b is not None and abs(b - a) <= tol}
                          for w, a, b, u, tol in checks]
    chans = CHANNELS.get(mod, {})
    d["alarms"] = [f"{chans[k][0]} reached {r[k]} {chans[k][1]}" for r in rows for k in r if k in chans and not chans[k][2] <= r[k] <= chans[k][3]][:5]
    d["channels"] = {k: {"label": v[0], "unit": v[1], "t": [(datetime.fromisoformat(r["ts"]) - datetime.fromisoformat(sess["ts"])).total_seconds() + 300 for r in rows if k in r],
                         "y": vals(k)} for k, v in chans.items() if vals(k)}
    return d


def measured_params(sess: dict, delivered: dict) -> dict:
    """Machine-measured inputs that replace the prescription when re-running the physiology prior."""
    p = dict(sess.get("params") or {})
    if delivered.get("measured_chamber_c") is not None:
        p["chamber_c"] = delivered["measured_chamber_c"]
    if delivered.get("measured_ata") is not None:
        p["ata"] = delivered["measured_ata"]
    if delivered.get("mean_o2_pct") is not None and sess["modality"].startswith("hbot"):
        p["o2_pct"] = delivered["mean_o2_pct"]
    if delivered.get("measured_temp_c") is not None:
        p["temp_c"] = delivered["measured_temp_c"]
    if delivered.get("mean_water_temp_c") is not None and sess["modality"] == "cold":
        p["water_c"] = delivered["mean_water_temp_c"]
    return p
