"""On-device Sinc: compact context and logging of phone answers."""
import os
import tempfile

os.environ.setdefault("TELOMY_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_context_is_compact_and_lines(client):
    r = client.get("/sinc/context", params={"q": "what about my ferritin?"}).json()
    assert r["system"].startswith("You are Sinc") and "Today:" in r["facts"]
    assert r["chars"] < 9000                       # fits a small model's working context
    assert "{" not in r["facts"].splitlines()[0]   # plain lines, not a JSON dump


def test_log_on_device_answer(client):
    r = client.post("/sinc/log", json={"question": "How did I sleep?", "answer": "About 7 hours on average.", "model": "Qwen3 1.7B"}).json()
    assert r["chat_id"] and r["message_id"] and "iPhone" in r["engine"]
    msgs = client.get(f"/sinc/chats/{r['chat_id']}").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert client.post("/sinc/log", json={"question": " ", "answer": "x"}).status_code == 400
