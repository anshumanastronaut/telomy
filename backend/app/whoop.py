"""WHOOP data via NOOP's self-hosted push (protocol 1.0, docs/PUSH_PROTOCOL.md in github.com/ryanbr/noop).

NOOP (an offline WHOOP companion on the user's own phone) can push its local database to an endpoint the user owns.
Telomy is that endpoint: raw strap streams (1 Hz HR, R-R intervals, 1 Hz gravity vector, respiration, skin temperature,
SpO2 red/IR) plus NOOP's own interpretation (sleep sessions with stages, daily recovery/strain/sleep). We store both so
Telomy's engines can be trained and graded against a second wearable worn the same nights.

This module implements the receiver contract only (no NOOP code is used): bearer auth with its own token
(TELOMY_WHOOP_TOKEN, separate from the app password), capability discovery, idempotent append batches, and atomic
multi-part replace-window delivery. Data stays on the Telomy server; nothing is sent anywhere else.
"""
import gzip
import hashlib
import hmac
import json
import os
import re
import uuid

from . import db

VERSION = "1.0"
MAX_NDJSON = 4 * 1024 * 1024
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# stream → (delivery, key columns in registry order, window selector or None)
REGISTRY = {
    "hrSample": ("append", ["ts"], None),
    "rrInterval": ("append", ["ts", "rrMs", "seq"], None),
    "event": ("append", ["ts", "kind"], None),
    "battery": ("append", ["ts"], None),
    "spo2Sample": ("append", ["ts"], None),
    "skinTempSample": ("append", ["ts"], None),
    "respSample": ("append", ["ts"], None),
    "gravitySample": ("append", ["ts"], None),
    "dailyMetric": ("replace_window", ["day"], "day"),
    "sleepSession": ("replace_window", ["startTs"], "startTs"),
    "workout": ("replace_window", ["startTs", "sport"], "startTs"),
    "journal": ("replace_window", ["day", "question"], "day"),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS whoop_state (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS whoop_rows (source_id TEXT, device_id TEXT, stream TEXT, key TEXT, ts INTEGER, day TEXT, data TEXT,
  PRIMARY KEY (source_id, device_id, stream, key)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS whoop_rows_ts ON whoop_rows (stream, ts);
CREATE TABLE IF NOT EXISTS whoop_batches (source_id TEXT, device_id TEXT, batch_id TEXT, sha TEXT, ack TEXT,
  PRIMARY KEY (source_id, device_id, batch_id));
CREATE TABLE IF NOT EXISTS whoop_staging (source_id TEXT, device_id TEXT, stream TEXT, replacement_id TEXT, part INTEGER, parts INTEGER,
  window TEXT, records TEXT, batch_id TEXT, PRIMARY KEY (source_id, device_id, stream, replacement_id, part));
CREATE TABLE IF NOT EXISTS whoop_superseded (source_id TEXT, device_id TEXT, stream TEXT, replacement_id TEXT,
  PRIMARY KEY (source_id, device_id, stream, replacement_id));
"""


class PushError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status, self.code = status, code


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)
        if not c.execute("SELECT 1 FROM whoop_state WHERE k='receiverStateId'").fetchone():
            c.execute("INSERT INTO whoop_state (k, v) VALUES ('receiverStateId', ?)", (str(uuid.uuid4()),))


def token_ok(header: str | None) -> bool:
    want = os.environ.get("TELOMY_WHOOP_TOKEN", "")
    if not want or not header or not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[7:].strip(), want)


def capabilities(accept: str | None) -> dict:
    offered = [v.strip() for v in (accept or "").split(",") if v.strip()]
    if VERSION not in offered:
        raise PushError(406, "unsupported_version")
    sid = db.one("SELECT v FROM whoop_state WHERE k='receiverStateId'")["v"]
    return {"type": "capabilities", "protocolVersion": VERSION, "receiverStateId": sid, "streams": list(REGISTRY)}


def _key_str(stream: str, key: dict) -> str:
    cols = REGISTRY[stream][1]
    if set(key) != set(cols):
        raise PushError(422, "invalid_key")
    return json.dumps({c: key[c] for c in cols}, separators=(",", ":"), ensure_ascii=False)


def _sel(stream: str, key: dict):
    """(ts, day) columns for range queries and window deletes."""
    k = REGISTRY[stream][1][0]
    v = key[k]
    return (v, None) if k in ("ts", "startTs") else (None, v)


def receive(raw: bytes, encoding: str | None) -> dict:
    if encoding and encoding.lower() == "gzip":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            raise PushError(400, "bad_gzip")
    elif encoding and encoding.lower() != "identity":
        raise PushError(415, "unsupported_encoding")
    if len(raw) > MAX_NDJSON:
        raise PushError(413, "too_large")
    sha = hashlib.sha256(raw).hexdigest()
    try:
        lines = raw.decode("utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        objs = [json.loads(l) for l in lines]
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PushError(400, "malformed_ndjson")
    if not objs or objs[0].get("type") != "batch":
        raise PushError(400, "missing_header")
    h, recs = objs[0], objs[1:]
    if h.get("protocolVersion") != VERSION:
        raise PushError(422, "unsupported_version")
    stream, src, dev, bid = h.get("stream"), h.get("sourceId"), h.get("deviceId"), h.get("batchId")
    if stream not in REGISTRY:
        raise PushError(422, "unknown_stream")
    if not (isinstance(src, str) and UUID_RE.match(src) and isinstance(bid, str) and UUID_RE.match(bid) and isinstance(dev, str) and dev):
        raise PushError(400, "bad_identity")
    delivery = REGISTRY[stream][0]
    if h.get("delivery") != delivery:
        raise PushError(422, "wrong_delivery")
    if h.get("recordCount") != len(recs) or len(recs) > 5000 or any(r.get("type") != "record" for r in recs):
        raise PushError(400, "bad_record_count")

    prev = db.one("SELECT sha, ack FROM whoop_batches WHERE source_id=? AND device_id=? AND batch_id=?", (src, dev, bid))
    if prev:
        if prev["sha"] != sha:
            raise PushError(409, "batch_conflict")
        return json.loads(prev["ack"])

    keyed = []
    seen = set()
    for r in recs:
        if not isinstance(r.get("key"), dict) or not isinstance(r.get("data"), dict):
            raise PushError(422, "invalid_record")
        ks = _key_str(stream, r["key"])
        if ks in seen:
            raise PushError(422, "duplicate_key")
        seen.add(ks)
        keyed.append((ks, r["key"], r["data"]))

    ack = {"protocolVersion": VERSION, "batchId": bid, "stream": stream, "deviceId": dev,
           "endCursor": h.get("endCursor") if delivery == "append" else None, "acceptedRows": len(recs), "status": "accepted"}

    with db.tx() as c:
        if delivery == "append":
            if not recs:
                raise PushError(400, "empty_append")
            _upsert(c, src, dev, stream, keyed)
        else:
            w = h.get("window") or {}
            rid, part, parts = w.get("replacementId"), w.get("part"), w.get("parts")
            if not (isinstance(rid, str) and UUID_RE.match(rid) and isinstance(part, int) and isinstance(parts, int) and 1 <= part <= parts):
                raise PushError(400, "bad_window")
            if w.get("selector") != REGISTRY[stream][2]:
                raise PushError(422, "wrong_selector")
            if c.execute("SELECT 1 FROM whoop_superseded WHERE source_id=? AND device_id=? AND stream=? AND replacement_id=?",
                         (src, dev, stream, rid)).fetchone():
                raise PushError(409, "superseded")
            win = json.dumps({k: w.get(k) for k in ("selector", "startInclusive", "endExclusive", "parts")}, sort_keys=True)
            for o in c.execute("SELECT DISTINCT replacement_id, window FROM whoop_staging WHERE source_id=? AND device_id=? AND stream=?",
                               (src, dev, stream)).fetchall():
                if o["replacement_id"] != rid:   # a new generation supersedes every older incomplete one
                    c.execute("DELETE FROM whoop_staging WHERE source_id=? AND device_id=? AND stream=? AND replacement_id=?",
                              (src, dev, stream, o["replacement_id"]))
                    c.execute("INSERT OR IGNORE INTO whoop_superseded VALUES (?,?,?,?)", (src, dev, stream, o["replacement_id"]))
                elif o["window"] != win:
                    raise PushError(409, "window_conflict")
            ex = c.execute("SELECT batch_id FROM whoop_staging WHERE source_id=? AND device_id=? AND stream=? AND replacement_id=? AND part=?",
                           (src, dev, stream, rid, part)).fetchone()
            if ex and ex["batch_id"] != bid:
                raise PushError(409, "part_conflict")
            c.execute("INSERT OR REPLACE INTO whoop_staging VALUES (?,?,?,?,?,?,?,?,?)",
                      (src, dev, stream, rid, part, parts, win, json.dumps([[k, kk, d] for k, kk, d in keyed]), bid))
            got = c.execute("SELECT part, records FROM whoop_staging WHERE source_id=? AND device_id=? AND stream=? AND replacement_id=?",
                            (src, dev, stream, rid)).fetchall()
            if len(got) == parts:          # complete → atomic upsert + delete absent keys in the window
                allrecs = [tuple(x) for g in got for x in json.loads(g["records"])]
                keys = [x[0] for x in allrecs]
                if len(set(keys)) != len(keys):
                    raise PushError(422, "duplicate_key")
                _upsert(c, src, dev, stream, allrecs)
                lo, hi = w.get("startInclusive"), w.get("endExclusive")
                col = "day" if REGISTRY[stream][2] == "day" else "ts"
                old = c.execute(f"SELECT key FROM whoop_rows WHERE source_id=? AND device_id=? AND stream=? AND {col} >= ? AND {col} < ?",
                                (src, dev, stream, lo, hi)).fetchall()
                keep = set(keys)
                for o in old:
                    if o["key"] not in keep:
                        c.execute("DELETE FROM whoop_rows WHERE source_id=? AND device_id=? AND stream=? AND key=?", (src, dev, stream, o["key"]))
                c.execute("DELETE FROM whoop_staging WHERE source_id=? AND device_id=? AND stream=? AND replacement_id=?", (src, dev, stream, rid))
                # closed: a retry of an applied part is answered from whoop_batches; any other reuse of this id is a conflict
                c.execute("INSERT OR IGNORE INTO whoop_superseded VALUES (?,?,?,?)", (src, dev, stream, rid))
        c.execute("INSERT INTO whoop_batches VALUES (?,?,?,?,?)", (src, dev, bid, sha, json.dumps(ack)))
    return ack


def _upsert(c, src, dev, stream, keyed):
    rows = []
    for ks, key, data in keyed:
        ts, day = _sel(stream, key)
        rows.append((src, dev, stream, ks, ts, day, json.dumps(data, separators=(",", ":"))))
    c.executemany("INSERT OR REPLACE INTO whoop_rows VALUES (?,?,?,?,?,?,?)", rows)


# ----------------------------------------------------------------------------- reading back (Telomy side)

def status() -> dict:
    rows = db.rows("SELECT stream, COUNT(*) AS n, MIN(COALESCE(ts, 0)) AS first, MAX(COALESCE(ts, 0)) AS last, MAX(day) AS lastDay "
                   "FROM whoop_rows GROUP BY stream")
    return {"configured": bool(os.environ.get("TELOMY_WHOOP_TOKEN")), "streams": {r["stream"]: dict(r) for r in rows}}


def series(stream: str, start: int, end: int, limit: int = 200000) -> list[dict]:
    out = []
    for r in db.rows("SELECT key, data FROM whoop_rows WHERE stream=? AND ts >= ? AND ts < ? ORDER BY ts LIMIT ?", (stream, start, end, limit)):
        out.append({**json.loads(r["key"]), **json.loads(r["data"])})
    return out


def nights(days: int = 30) -> list[dict]:
    """NOOP's sleep sessions (its interpretation of the WHOOP strap), newest last."""
    out = []
    for r in db.rows("SELECT key, data FROM whoop_rows WHERE stream='sleepSession' ORDER BY ts DESC LIMIT ?", (days * 2,)):
        k, d = json.loads(r["key"]), json.loads(r["data"])
        st = d.get("stagesJSON")
        try:
            st = json.loads(st) if isinstance(st, str) else st
        except json.JSONDecodeError:
            st = None
        out.append({"start": k["startTs"], "end": d.get("endTs"), "efficiency": d.get("efficiency"), "restingHr": d.get("restingHr"),
                    "avgHrv": d.get("avgHrv"), "stages": st, "userEdited": d.get("userEdited")})
    return out[::-1]


def daily(days: int = 30) -> list[dict]:
    return [{"day": r["day"], **json.loads(r["data"])}
            for r in db.rows("SELECT day, data FROM whoop_rows WHERE stream='dailyMetric' ORDER BY day DESC LIMIT ?", (days,))][::-1]
