"""NOOP self-hosted push receiver (protocol 1.0) — contract tests with synthetic records only."""
import gzip
import json
import os
import tempfile
import uuid

os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
os.environ.setdefault("TELOMY_TODAY", "2026-10-06")
os.environ["TELOMY_WHOOP_TOKEN"] = "test-whoop-token"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

AUTH = {"Authorization": "Bearer test-whoop-token"}
SRC = str(uuid.uuid4())


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def ndjson(header, records):
    lines = [json.dumps(header)] + [json.dumps({"type": "record", **r}) for r in records]
    return ("\n".join(lines) + "\n").encode()


def post(client, body, gz=True):
    h = {**AUTH, "Content-Type": "application/x-ndjson; charset=utf-8"}
    if gz:
        body, h["Content-Encoding"] = gzip.compress(body), "gzip"
    return client.post("/whoop/push", content=body, headers=h)


def test_capabilities_need_token_and_version(client):
    assert client.get("/whoop/push").status_code == 401
    assert client.get("/whoop/push", headers={**AUTH, "NOOP-Push-Accept-Version": "2.0"}).status_code == 406
    c = client.get("/whoop/push", headers={**AUTH, "NOOP-Push-Accept-Version": "1.0"}).json()
    assert c["type"] == "capabilities" and c["protocolVersion"] == "1.0" and "gravitySample" in c["streams"] and len(c["streams"]) == 12


def test_append_is_idempotent_and_conflicts_are_rejected(client):
    bid = str(uuid.uuid4())
    h = {"type": "batch", "protocolVersion": "1.0", "batchId": bid, "sourceId": SRC, "deviceId": "strap1", "stream": "hrSample",
         "delivery": "append", "recordCount": 2, "startCursor": None, "endCursor": {"rowId": 2, "keySha256": "b" * 64}}
    body = ndjson(h, [{"key": {"ts": 1000}, "data": {"bpm": 61}}, {"key": {"ts": 1001}, "data": {"bpm": 62}}])
    a = post(client, body).json()
    assert a == {"protocolVersion": "1.0", "batchId": bid, "stream": "hrSample", "deviceId": "strap1",
                 "endCursor": {"rowId": 2, "keySha256": "b" * 64}, "acceptedRows": 2, "status": "accepted"}
    assert post(client, body, gz=False).json() == a                       # same entity, other coding → same ack
    other = ndjson({**h, "recordCount": 1}, [{"key": {"ts": 1002}, "data": {"bpm": 70}}])
    r = post(client, other)
    assert r.status_code == 409 and r.json()["code"] == "batch_conflict"
    assert client.get("/whoop/status").json()["streams"]["hrSample"]["n"] == 2


def test_replace_window_multipart_deletes_absent_rows(client):
    def part(rid, n, parts, recs):
        h = {"type": "batch", "protocolVersion": "1.0", "batchId": str(uuid.uuid4()), "sourceId": SRC, "deviceId": "strap1",
             "stream": "sleepSession", "delivery": "replace_window", "recordCount": len(recs), "startCursor": None, "endCursor": None,
             "window": {"replacementId": rid, "selector": "startTs", "startInclusive": 0, "endExclusive": 10_000, "part": n, "parts": parts}}
        return post(client, ndjson(h, recs))
    s = lambda t: {"key": {"startTs": t}, "data": {"endTs": t + 100, "userEdited": False, "stagesJSON": "[]"}}
    r1 = str(uuid.uuid4())
    assert part(r1, 1, 2, [s(100)]).json()["status"] == "accepted"
    assert len(client.get("/whoop/nights").json()["nights"]) == 0        # not applied until every part is in
    part(r1, 2, 2, [s(200)])
    assert [n["start"] for n in client.get("/whoop/nights").json()["nights"]] == [100, 200]
    r2 = str(uuid.uuid4())
    part(r2, 1, 1, [s(200)])                                               # 100 is gone from the authoritative window
    assert [n["start"] for n in client.get("/whoop/nights").json()["nights"]] == [200]
    assert part(r1, 1, 2, [s(300)]).status_code == 409                    # late part of a superseded/complete generation
