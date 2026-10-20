"""Trackers built by talking to Sinc — synthetic statements only."""
import os
import tempfile

os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app import trackers  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("text,kind,value", [
    ("my lower back hurts, about 6/10", "pain", 6.0), ("knee pain 4 after running", "pain", 4.0),
    ("had a mild headache yesterday", "symptom", 3), ("track my migraines", "symptom", None),
    ("I started magnesium 200 mg before bed", "supplement", 1.0), ("started metformin 500 mg with dinner", "medicine", 1.0),
    ("I want to quit sugar", "habit_break", None), ("start meditating every morning", "habit_build", None),
    ("weight 92.4 kg", "measure", 92.4), ("track how often I bite my nails", "custom", None),
])
def test_understands(client, text, kind, value):
    it = trackers.understand(text)["items"][0]
    assert it["kind"] == kind and it.get("value") == value


def test_red_flags_and_questions(client):
    assert trackers.understand("I have chest pain")["red_flag"]
    assert trackers.understand("I don't want to live anymore")["red_flag"]
    assert trackers.capture("why is my hrv low?") is None


def test_sinc_sets_up_tracker_then_follow_up_number(client):
    r = client.post("/sinc/ask", json={"question": "feeling bloated after dinner"}).json()
    assert r["engine"] == "telomy-trackers" and r["trackers"][0]["new"] and "0–10" in r["answer"]
    r2 = client.post("/sinc/ask", json={"question": "6", "chat_id": r["chat_id"]}).json()
    assert "logged 6/10" in r2["answer"]
    tid = r["trackers"][0]["id"]
    t = client.get(f"/trackers/{tid}").json()
    assert t["entries"][0]["value"] == 6 and t["drivers"]["ready"] is False
    assert client.post(f"/trackers/{tid}/entry", json={"value": 3}).json()["entries"] == 2


def test_red_flag_answer_points_to_care(client):
    r = client.post("/sinc/capture", json={"text": "sudden worst headache of my life"}).json()
    assert r["captured"] and r["red_flag"] and "112" in r["answer"]


def test_drivers_find_planted_pattern(client):
    from app import db, engine
    from datetime import date, timedelta
    tr, _ = trackers._ensure({"kind": "symptom", "key": "sym_test_planted", "name": "Planted", "ts": engine.now_iso()}, "test")
    d0 = date(2025, 1, 1)
    import random
    rnd = random.Random(3)
    for i in range(40):
        d = (d0 + timedelta(days=i)).isoformat()
        sl = 5 + rnd.random() * 4
        db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (d, "sleep_hours", sl, "test"))
        trackers.log_entry(tr["id"], round(max(0, min(10, 14 - 1.4 * sl + rnd.gauss(0, 0.6))), 1), d + "T21:00")
    r = trackers.drivers(tr["id"])
    assert r["ready"] and any("Sleep duration (same day)" in f["driver"] and f["rho"] < 0 for f in r["found"])
