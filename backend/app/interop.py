"""Interoperability — make the platform OPEN to hospital/EHR systems and existing software:
  * FHIR-style export of a patient as Patient / Observation / DiagnosticReport resources (HL7 FHIR R4 shapes), so an
    external EHR can read Telomy data.
  * Outbound webhooks: register a URL + events (order.updated, booking.created, note.signed, lab.result); Telomy POSTs
    a signed JSON payload when they happen, so external systems stay in sync.
  * API keys: scoped keys an integration uses to call the platform API (read/write), independent of user sessions.
This is the integration surface; it keeps Telomy a good citizen in a hospital's existing stack.
"""
import hashlib
import hmac
import json
import secrets
import time
import urllib.request

from . import db, engine
from .catalog import MARKERS

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, name TEXT, prefix TEXT, hash TEXT,
  scopes TEXT, created_at REAL, last_used REAL, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS webhooks (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, url TEXT, events TEXT, secret TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS webhook_log (id INTEGER PRIMARY KEY AUTOINCREMENT, hook_id INTEGER, ts REAL, event TEXT, status INTEGER);
"""


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ---- FHIR export ------------------------------------------------------------------------------------------------

def fhir_patient() -> dict:
    p = engine.profile()
    age = engine.age_on()
    return {"resourceType": "Patient", "id": "telomy-1",
            "name": [{"text": p.get("first_name") or "Patient"}],
            "gender": p.get("sex"), "extension": [{"url": "chronological-age", "valueDecimal": round(age, 1) if age else None}]}


_UCUM = {"mg/dL": "mg/dL", "mmol/L": "mmol/L", "%": "%", "U/L": "U/L", "ng/mL": "ng/mL", "g/dL": "g/dL", "mg/L": "mg/L"}


def fhir_observations() -> list[dict]:
    out = []
    for k, r in engine.latest_values().items():
        spec = MARKERS.get(k)
        if not spec or r["value_num"] is None:
            continue
        loinc = spec[7] if len(spec) > 7 else ""
        out.append({"resourceType": "Observation", "status": "final",
                    "code": {"coding": ([{"system": "http://loinc.org", "code": loinc}] if loinc else []), "text": spec[0]},
                    "valueQuantity": {"value": r["value_num"], "unit": r["unit"], "system": "http://unitsofmeasure.org",
                                      "code": _UCUM.get(r["unit"], r["unit"])},
                    "effectiveDateTime": r["collected_on"], "subject": {"reference": "Patient/telomy-1"}})
    return out


def fhir_bundle() -> dict:
    entries = [{"resource": fhir_patient()}] + [{"resource": o} for o in fhir_observations()]
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


# ---- API keys ---------------------------------------------------------------------------------------------------

def create_key(org: str, name: str, scopes: list[str]) -> dict:
    raw = secrets.token_urlsafe(32)
    prefix = raw[:8]
    h = hashlib.sha256(raw.encode()).hexdigest()
    db.exec_("INSERT INTO api_keys (org, name, prefix, hash, scopes, created_at, active) VALUES (?,?,?,?,?,?,1)",
             (org, name[:80], prefix, h, db.j(scopes), time.time()))
    return {"name": name, "key": raw, "prefix": prefix, "scopes": scopes,
            "note": "Store this key now — it is not shown again."}


def verify_key(raw: str) -> dict | None:
    if not raw:
        return None
    h = hashlib.sha256(raw.encode()).hexdigest()
    r = db.one("SELECT * FROM api_keys WHERE hash = ? AND active = 1", (h,))
    if r:
        db.exec_("UPDATE api_keys SET last_used = ? WHERE id = ?", (time.time(), r["id"]))
        return {"org": r["org"], "scopes": db.unj(r["scopes"], [])}
    return None


def list_keys(org: str) -> list[dict]:
    return [{"id": r["id"], "name": r["name"], "prefix": r["prefix"], "scopes": db.unj(r["scopes"], []),
             "active": r["active"], "last_used": r["last_used"]} for r in db.rows("SELECT * FROM api_keys WHERE org = ?", (org,))]


def revoke_key(kid: int):
    db.exec_("UPDATE api_keys SET active = 0 WHERE id = ?", (kid,))


# ---- webhooks ---------------------------------------------------------------------------------------------------

def add_webhook(org: str, url: str, events: list[str]) -> dict:
    secret = secrets.token_urlsafe(24)
    hid = db.exec_("INSERT INTO webhooks (org, url, events, secret, active) VALUES (?,?,?,?,1)", (org, url, db.j(events), secret))
    return {"id": hid, "url": url, "events": events, "secret": secret}


def list_webhooks(org: str) -> list[dict]:
    return [{"id": r["id"], "url": r["url"], "events": db.unj(r["events"], []), "active": r["active"]}
            for r in db.rows("SELECT * FROM webhooks WHERE org = ?", (org,))]


def fire(org: str, event: str, payload: dict):
    """POST a signed payload to every webhook subscribed to this event (best-effort, logged)."""
    for r in db.rows("SELECT * FROM webhooks WHERE org = ? AND active = 1", (org,)):
        if event not in db.unj(r["events"], []) and "*" not in db.unj(r["events"], []):
            continue
        body = json.dumps({"event": event, "ts": time.time(), "data": payload}).encode()
        sig = hmac.new(r["secret"].encode(), body, hashlib.sha256).hexdigest()
        req = urllib.request.Request(r["url"], data=body, headers={"Content-Type": "application/json", "X-Telomy-Signature": sig})
        status = 0
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
        except Exception:  # noqa: BLE001
            status = -1
        db.exec_("INSERT INTO webhook_log (hook_id, ts, event, status) VALUES (?,?,?,?)", (r["id"], time.time(), event, status))
