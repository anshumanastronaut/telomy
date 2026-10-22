"""Telomy LLM wrapper: provider selection, the number guard, and graceful fallback."""
import importlib
import os


def _fresh(**env):
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "TELOMY_USE_CLAUDE", "TELOMY_LLM_BASE_URL"):
        os.environ.pop(k, None)
    os.environ.update(env)
    import app.telomy_llm as m
    return importlib.reload(m)


def test_provider_selection():
    assert _fresh().provider() is None
    assert _fresh(TELOMY_USE_CLAUDE="1").provider() == "anthropic"
    assert _fresh(TELOMY_LLM_BASE_URL="http://x/v1").provider() == "openai"


def test_no_provider_returns_none():
    m = _fresh()
    assert m.ask("sys", "facts", "q?", [], {}) is None


def test_number_guard():
    m = _fresh()
    facts = "Lab Platelets: 96 10³/µL on 2026-08-20\nSignal HRV: 49 ms"
    assert m.ungrounded("Your platelets were 96 and HRV 49 ms. Two points to note.", facts, "platelets?") == []
    bad = m.ungrounded("Take 2 mg folate; your HRV is 52 ms.", facts, "")
    assert 2 in bad and 52 in bad


def test_guard_rejects_invented_numbers(monkeypatch):
    m = _fresh(TELOMY_LLM_BASE_URL="http://x/v1")
    monkeypatch.setattr(m, "_call_openai", lambda *a, **k: {"answer": "Your LDL is 205 mg/dL.", "engine": "mock"})
    r = m.ask("sys", "LDL 148 mg/dL on 2026-08-20", "ldl?", [], {})
    assert r and "_error" in r and "ungrounded" in r["_error"]


def test_grounded_answer_passes(monkeypatch):
    m = _fresh(TELOMY_LLM_BASE_URL="http://x/v1")
    monkeypatch.setattr(m, "_call_openai", lambda *a, **k: {"answer": "Your LDL is 148 mg/dL — above the optimal 100.",
                                                            "evidence_ids": ["ldl"], "confidence": 0.8, "medical": True, "engine": "mock"})
    r = m.ask("sys", "LDL 148 mg/dL (optimal < 100) on 2026-08-20", "ldl?", [], {})
    assert r and r["answer"].startswith("Your LDL") and r["medical"] is True and "_error" not in r
