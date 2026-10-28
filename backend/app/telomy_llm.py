"""Telomy LLM wrapper — one entry point Sinc (and anything else) uses to reach a language model, chosen to serve the
person's interest, not a vendor's:

  * Provider-agnostic. In priority order from the environment:
      1. Anthropic (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN) — best quality.
      2. Any OpenAI-compatible endpoint (TELOMY_LLM_BASE_URL + TELOMY_LLM_API_KEY + TELOMY_LLM_MODEL). This covers the
         free routes: a local OmniRoute/llama.cpp server, OpenRouter's free tier, Groq, Together, etc. No new dependency —
         plain HTTPS. Set TELOMY_LLM_BASE_URL and it is used.
      3. None configured → caller falls back to the deterministic composer.
  * Grounded + guarded. Every answer must be JSON {answer, evidence_ids, confidence, medical}. A guard then checks that
    each number in the answer appears in the grounding context (or the question); if one is invented, the wrapper rejects
    the answer so the caller falls back. Numbers are the thing a small model gets wrong, and a wrong lab value is worse
    than a plain one.
  * Efficient. A short-lived response cache (same question + same context → same answer) and a hard timeout, so a slow or
    stuck provider never hangs the app — it degrades to the composer instead.
"""
import hashlib
import json
import os
import re
import time
import urllib.request

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 900


def provider() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("TELOMY_USE_CLAUDE"):
        return "anthropic"
    if os.environ.get("TELOMY_LLM_BASE_URL"):
        return "openai"
    return None


def available() -> bool:
    return provider() is not None


def model_name() -> str:
    p = provider()
    if p == "anthropic":
        return os.environ.get("TELOMY_LLM_MODEL", "claude-opus-4-8")
    if p == "openai":
        return os.environ.get("TELOMY_LLM_MODEL", "auto")
    return "telomy-retrieval"


# ---- the number-grounding guard (mirrors mobile/src/lib/slm.ts) ------------------------------------------------------

_NUM = re.compile(r"(\d+(?:\.\d+)?)(\s*(?:mg|mcg|µg|iu|ml|%|kg|kcal|g|tablets?|capsules?|units?)\b)?", re.I)


def _nums(s: str) -> set[float]:
    return {round(float(x), 2) for x in re.findall(r"\d+(?:\.\d+)?", re.sub(r"(\d),(\d{3})", r"\1\2", s))}


def ungrounded(answer: str, context: str, question: str) -> list[float]:
    known = _nums(context) | _nums(question)
    bad = []
    for m in _NUM.finditer(re.sub(r"(\d),(\d{3})", r"\1\2", answer)):
        n = round(float(m.group(1)), 2)
        if n in known:
            continue
        if n == int(n) and n <= 10 and not m.group(2):   # small bare counts ("2 things", "1.") are fine
            continue
        bad.append(n)
    return bad


# ---- providers -------------------------------------------------------------------------------------------------------

def _call_anthropic(system: str, user: str, history: list[dict], schema: dict, max_tokens: int, timeout: float,
                    images: list[dict] | None = None) -> dict:
    import anthropic
    client = anthropic.Anthropic(timeout=timeout)
    msgs = [{"role": m["role"], "content": m["content"]} for m in history[-10:] if m["role"] in ("user", "assistant")]
    if images:  # Claude is multimodal: send the text plus each image as content blocks
        content: list[dict] = [{"type": "text", "text": user}]
        for im in images:
            content.append({"type": "image", "source": {"type": "base64",
                           "media_type": im.get("media_type", "image/jpeg"), "data": im["data"]}})
        msgs.append({"role": "user", "content": content})
    else:
        msgs.append({"role": "user", "content": user})
    # Standard Messages API + JSON-in-prompt (stable across SDK/model versions; the beta output_config shape the API
    # rejected with a 400 is gone). The caller's grounding guard still checks the returned answer against the context.
    sysmsg = system + ('\n\nReturn ONLY a single JSON object and nothing else: '
                       '{"answer": string, "evidence_ids": [string], "confidence": number between 0 and 1, "medical": boolean}.')
    resp = client.messages.create(model=model_name(), max_tokens=max_tokens, system=sysmsg, messages=msgs)
    if getattr(resp, "stop_reason", None) == "refusal":
        return {"_refusal": True, "engine": resp.model}
    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "{}")
    m = re.search(r"\{.*\}", text, re.S)
    out = json.loads(m.group(0) if m else text)
    out["engine"] = resp.model
    return out


def _call_openai(system: str, user: str, history: list[dict], schema: dict, max_tokens: int, timeout: float,
                 images: list[dict] | None = None) -> dict:
    if images:  # the OpenAI-compatible on-prem path is text-only here; say so rather than silently dropping them
        user += f"\n\n[The user attached {len(images)} image(s), but this on-device model can't view images. " \
                "Answer from the text and suggest they view images on the cloud Sinc.]"
    base = os.environ["TELOMY_LLM_BASE_URL"].rstrip("/")
    key = os.environ.get("TELOMY_LLM_API_KEY", "")
    msgs = [{"role": "system", "content": system + "\nReply with ONLY a JSON object matching: "
             '{"answer": str, "evidence_ids": [str], "confidence": number 0-1, "medical": bool}. No prose outside the JSON.'}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in history[-10:] if m["role"] in ("user", "assistant")]
    msgs.append({"role": "user", "content": user})
    body = json.dumps({"model": model_name(), "messages": msgs, "max_tokens": max_tokens, "temperature": 0.3,
                       "response_format": {"type": "json_object"}}).encode()
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    content = data["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", content, re.S)
    out = json.loads(m.group(0) if m else content)
    out["engine"] = data.get("model", model_name())
    return out


# ---- the one entry point ---------------------------------------------------------------------------------------------

def ask(system: str, context: str, question: str, history: list[dict], schema: dict,
        max_tokens: int = 4000, timeout: float = 25.0,
        images: list[dict] | None = None, skip_guard: bool = False) -> dict | None:
    """Return a grounded {answer, evidence_ids, confidence, medical, engine} dict, or None when no provider is
    configured, the call fails/times out, or the answer uses numbers that aren't in the context (guard tripped).
    `images` are passed to a vision-capable provider; `skip_guard` bypasses the numbers-in-context check (used when
    the user attached files, which are their own grounding)."""
    p = provider()
    if not p:
        return None
    images = images or []
    user = f"CONTEXT:\n{context}\n\nQUESTION: {question}"
    # one-off calls (anything with an image) must not be served from, or written to, the shared cache
    use_cache = not images and not skip_guard
    key = hashlib.sha1(f"{p}|{system}|{user}".encode()).hexdigest()
    if use_cache:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return dict(hit[1])
    try:
        if p == "anthropic":
            out = _call_anthropic(system, user, history, schema, max_tokens, timeout, images=images)
        else:
            out = _call_openai(system, user, history, schema, max_tokens, timeout, images=images)
    except Exception as exc:  # noqa: BLE001 — any provider error degrades to the composer
        return {"_error": f"{type(exc).__name__}: {str(exc)[:120]}"}
    if out.get("_refusal"):
        return {"answer": "I can't help with that one. If it's about your health data, try asking it another way.",
                "evidence_ids": [], "confidence": 0, "medical": False, "engine": out.get("engine", model_name())}
    ans = str(out.get("answer") or "").strip()
    if not ans:
        return {"_error": "empty answer"}
    if not skip_guard:
        bad = ungrounded(ans, context, question)
        if bad:
            return {"_error": f"ungrounded numbers {bad[:3]}"}
    out.setdefault("evidence_ids", [])
    out.setdefault("confidence", 0.7)
    out.setdefault("medical", False)
    out["engine"] = out.get("engine", model_name())
    if use_cache:
        if len(_CACHE) > 200:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (time.time(), out)
    return out
