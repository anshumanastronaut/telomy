"""Sinc — Telomy's companion.

Two backends behind one interface:
  * Claude (claude-opus-5-5) when ANTHROPIC_API_KEY / an `ant` profile is available — grounded on a context
    pack built from the Vault, structured JSON output so evidence ids and confidence are machine-readable.
  * A deterministic retrieval composer otherwise — answers only from engine insights and stored values.

Voice rules (UI Design System §14.3): first person, warm, precise, no enthusiasm words, no exclamation marks,
numbers with their windows, confidence not certainty, admit missing data, offer a clinician draft for
medical-adjacent questions.
"""
import json
import os
import re
from datetime import datetime

from . import db, engine
from .catalog import MARKERS

MODEL = "claude-opus-5-5"
MEDICAL_WORDS = re.compile(r"\b(should i take|dose|dosage|medicat|statin|metformin|prescri|diagnos|disease|cancer|"
                           r"diabet|treat|cure|supplement|start taking|stop taking|risk of|chelat|is it serious)\b", re.I)

SYSTEM = """You are Sinc, the health companion inside Telomy, a longevity app.
Answer only from the CONTEXT (the person's own Vault: lab results, wearable signals, logged events and the
engine's insights). Rules:
- Speak in first person, warm and precise. Never use "amazing", "great", "awesome". No exclamation marks. No emoji.
- Give numbers with their time windows and sources ("hs-CRP 3.4 mg/L on 1 Oct, up from 2.1 in July").
- Say "emerging pattern" / "strong correlation", never "proven". Correlations in personal data are not causes.
- If the context lacks the data, say exactly what is missing and how to get it.
- Never diagnose or prescribe. For medical-adjacent questions, end by offering to draft a note for the clinician.
- Keep it under 220 words unless asked for detail. Plain English before technical terms.
Return JSON matching the schema: answer (markdown allowed), evidence_ids (insight ids or marker ids you used),
confidence (0-1), medical (true if medical-adjacent)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "medical": {"type": "boolean"},
    },
    "required": ["answer", "evidence_ids", "confidence", "medical"],
    "additionalProperties": False,
}


def context_pack() -> dict:
    p = engine.profile()
    latest = engine.latest_values()
    labs = [{"id": k, "name": MARKERS[k][0], "value": v["value_num"] if v["value_num"] is not None else v["value_text"],
             "unit": v["unit"], "status": v["status"], "date": v["collected_on"], "lab_range": v["ref_text"],
             "trend": engine.marker_trend(k)} for k, v in latest.items()]
    signals = {}
    for m in engine.SIGNALS:
        b = engine.signal_baseline(m, days=30)
        if b:
            signals[m] = {"label": engine.SIGNALS[m][0], "unit": engine.SIGNALS[m][1], "mean_30d": b["mean"], "n": b["n"]}
    insights = [{"id": i["id"], "title": i["title"], "body": i["body"], "confidence": i["confidence"],
                 "review_state": i["review_state"]} for i in engine.list_insights()[:30]]
    memories = [m["fact"] for m in db.rows("SELECT fact FROM memories ORDER BY ts DESC LIMIT 20")]
    return {"profile": {"first_name": p.get("first_name"), "age": round(engine.age_on() or 0, 1), "sex": p.get("sex"),
                        "goal": p.get("goal")},
            "longevity_age": {k: engine.longevity_age().get(k) for k in ("value", "chronological", "pace", "confidence")},
            "labs": labs, "signals_30d": signals, "insights": insights, "memories": memories,
            "today": (engine.last_signal_day() or datetime.now().date().isoformat())}


def _claude_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.environ.get("TELOMY_USE_CLAUDE"))


def _ask_claude(question: str, history: list[dict]) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    msgs = [{"role": m["role"], "content": m["content"]} for m in history[-10:] if m["role"] in ("user", "assistant")]
    msgs.append({"role": "user", "content": f"CONTEXT:\n{json.dumps(context_pack(), default=str)}\n\nQUESTION: {question}"})
    kwargs = dict(model=MODEL, max_tokens=16000, system=SYSTEM, messages=msgs,
                  output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}})
    try:
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    except TypeError:
        resp = client.messages.create(**kwargs)
    if resp.stop_reason == "refusal":
        return {"answer": "I can't help with that one. If it's about your health data, try asking it another way.",
                "evidence_ids": [], "confidence": 0, "medical": False, "engine": MODEL}
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    out = json.loads(text)
    out["engine"] = resp.model
    return out


STOP = set("""the and for are was were with what why how this that these those my your you our from into have has had
does did doing done when which who whom been being about over under than then there their them they its it's not but
can could should would will just also more most less least very much many lower higher low high month week year today
day days last next some any all each other own same such only tell show mean means change changed get got""".split())


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9\-]+", s.lower()) if len(w) > 2 and w not in STOP}


def _period_compare(metric: str) -> str | None:
    end = engine.last_signal_day()
    if not end:
        return None
    from datetime import date, timedelta
    e = date.fromisoformat(end)
    cur = [v for _, v in engine.series(metric, (e - timedelta(days=29)).isoformat(), end)]
    prev = [v for _, v in engine.series(metric, (e - timedelta(days=59)).isoformat(), (e - timedelta(days=30)).isoformat())]
    if len(cur) < 10 or len(prev) < 10:
        return None
    lab, unit, _, dec = engine.SIGNALS[metric]
    a, b = sum(cur) / len(cur), sum(prev) / len(prev)
    d = a - b
    return (f"Your {engine.lc(lab)} averaged **{round(a, dec or 1)} {unit}** over the last 30 days, "
            f"{'down' if d < 0 else 'up'} {abs(round(d, dec or 1))} {unit} from {round(b, dec or 1)} the 30 days before (n = {len(cur)} and {len(prev)} nights).")


ALIASES = {"sleep": ["sleep_hours", "deep_sleep", "sleep_score"], "heart": ["rhr"], "hrv": ["hrv"], "variability": ["hrv"],
           "rhr": ["rhr"], "resting": ["rhr"], "deep": ["deep_sleep"], "spo2": ["spo2"], "oxygen": ["spo2"],
           "steps": ["steps"], "glucose": ["glucose_mean"], "weight": ["weight"], "fitness": ["vo2max"],
           "recovery": ["hrv", "rhr", "sleep_score"], "stress": ["hrv"]}
CROSS_WORDS = re.compile(r"\b(all (my )?(lab )?reports|correlat|connect|link|across|together|compare|changed|pattern|overall|summary|big picture)\b", re.I)


def _compose(question: str) -> dict:
    q = question.lower()
    toks = _tokens(q)
    latest = engine.latest_values()
    insights = engine.list_insights()
    parts, evidence, conf = [], [], []

    if CROSS_WORDS.search(q):
        cross = [i for i in insights if i["kind"] in ("cross_panel", "lab_wearable")][:5]
        trends = [i for i in insights if i["kind"] == "lab_trend"][:5]
        if cross:
            parts.append("Here is what I see when I read your reports together:")
            for i in cross:
                parts.append(f"- **{i['title']}.** {i['body']} _(confidence {int(i['confidence'] * 100)}%)_")
                evidence.append(i["id"]); conf.append(i["confidence"])
        if trends:
            parts.append("\nBetween your two most recent blood panels:")
            parts.append("\n".join(f"- {t['title']}" for t in trends))
            evidence += [t["id"] for t in trends]
    else:
        hits = []
        for mid, spec in MARKERS.items():
            names = [spec[0].lower()] + spec[6]
            if mid in latest and any(n in q for n in names if len(n) > 2):
                hits.append(mid)
        for mid in hits[:4]:
            r = latest[mid]
            val = r["value_num"] if r["value_num"] is not None else r["value_text"]
            t = engine.marker_trend(mid)
            line = f"Your {MARKERS[mid][0]} was {val} {r['unit'] or ''} on {r['collected_on']} (lab range {r['ref_text'] or 'n/a'})."
            if t:
                line += f" It was {t['from']} on {t['from_day']}, so it has {('improved' if t['direction'] == 'better' else 'moved the wrong way')}."
            parts.append(line)
            evidence.append(mid)
        metrics = {m for w in toks for m in ALIASES.get(w, [])}
        for m in sorted(metrics):
            cmp = _period_compare(m)
            if cmp:
                parts.append(cmp)
                evidence.append(m)
        labels = {engine.SIGNALS[m][0].lower().split(" (")[0] for m in metrics}
        scored = []
        for i in insights:
            text = (i["title"] + " " + i["body"]).lower()
            ev_metrics = {e.get("metric") for e in i["evidence"]}
            score = 3 * len(ev_metrics & metrics) + 2 * sum(1 for l in labels if l in text)
            score += len(toks & _tokens(text)) + 2 * sum(1 for h in hits if any(e.get("marker_id") == h for e in i["evidence"]))
            if re.search(r"\b(lower|drop|down|worse|fell|declin)", q) and i["receipts"].get("direction") == "harmful":
                score += 3
            if score >= 3:
                scored.append((score, i))
        if scored and metrics:
            parts.append("\nWhat in your data moves with it:")
        for _, i in sorted(scored, key=lambda x: (-x[0], -x[1]["confidence"]))[:4]:
            parts.append(f"\n**{i['title']}.** {i['body']} _(confidence {int(i['confidence'] * 100)}%)_")
            evidence.append(i["id"]); conf.append(i["confidence"])

    if not parts:
        parts.append("I don't have enough signal in your Vault to answer that yet. If you log it, or add the relevant "
                     "report, I'll be able to say more. You can ask me about any biomarker, your sleep, HRV, or how "
                     "your reports connect.")
    medical = bool(MEDICAL_WORDS.search(q))
    if medical:
        parts.append("\nThis is worth talking to your clinician about. I can draft a note with these numbers for "
                     "them to review.")
    return {"answer": "\n".join(parts), "evidence_ids": evidence, "medical": medical,
            "confidence": min(0.9, round(sum(conf) / len(conf), 2)) if conf else (0.6 if evidence else 0.0),
            "engine": "telomy-retrieval 0.1"}


MEMORY_PAT = re.compile(r"\b(i (?:am|prefer|take|don't|do not|avoid|train|work|eat|have)\b[^.?!]{3,80})", re.I)


def _deep_refs(out: dict) -> list[dict]:
    from .evidence import EVENT_REFS, MARKER_REFS, RULE_REFS, cite
    keys = []
    by_id = {i["id"]: i for i in engine.list_insights(include_dismissed=True)}
    used = 0
    for e in out.get("evidence_ids", []):
        i = by_id.get(e)
        if i and used < 2:
            used += 1
            keys += RULE_REFS.get(i["receipts"].get("rule"), [])
            for ev in i["evidence"]:
                keys += MARKER_REFS.get(ev.get("marker_id"), [])
            if i["kind"] == "event_effect":
                keys += EVENT_REFS.get(next((k for k in EVENT_REFS if k in i["title"].lower()), ""), [])
        keys += MARKER_REFS.get(e, [])
    return cite(keys)[:8]


DEEP_WORDS = re.compile(r"\b(why|how|explain|compare|connect|research|mechanism|cellular|deep dive|root cause|what causes|"
                       r"should i|is it serious|everything about|full picture|overall|across)\b", re.I)


def looks_deep(question: str) -> bool:
    toks = _tokens(question)
    markers_hit = sum(1 for m in MARKERS if any(n in question.lower() for n in [MARKERS[m][0].lower()] + list(MARKERS[m][6] if isinstance(MARKERS[m][6], list) else [])))
    return bool(DEEP_WORDS.search(question)) or len(question) > 90 or markers_hit >= 2 or len(toks) >= 12


def _deep_compose(question: str) -> dict:
    """RAG-first deep research without a cloud model: broad retrieval across the Vault, the cross-domain threads it
    touches, the cellular mechanisms behind the markers involved, and the literature — structured and grounded. When a
    provider (e.g. Anthropic) is configured, the wrapper handles deep mode instead and this is the fallback."""
    from . import retrieval, cellular
    cards = retrieval.retrieve(question, k=24)
    by = {}
    for c in cards:
        by.setdefault(c["kind"], []).append(c)
    parts, evidence, markers_used = [], [], []
    # 1) what your data shows
    labs = by.get("lab", [])[:8]; sigs = by.get("signal", [])[:6]
    if labs or sigs:
        parts.append("**What your data shows**")
        for c in labs + sigs:
            parts.append(f"- {c['text']}")
            mid = c["id"].split(":", 1)[1]
            if mid in MARKERS: markers_used.append(mid)
            evidence.append(mid)
    # 2) what connects (cross-domain threads touching this question)
    qtok = _tokens(question)
    threads = [t for t in retrieval.connect().get("threads", []) if _tokens(t["headline"]) & qtok or _tokens(t["theme"]) & qtok]
    if not threads:
        threads = retrieval.connect().get("threads", [])[:2]
    if threads:
        parts.append("\n**What connects**")
        for t in threads[:3]:
            parts.append(f"- _{t['theme']}_: {t['story']}")
            evidence.append(t["insight_id"])
    # 3) cellular level
    cell = []
    for m in dict.fromkeys(markers_used):
        cell += cellular.for_marker(m)
    seen=set(); cell=[e for e in cell if not (e["name"] in seen or seen.add(e["name"]))][:5]
    if cell:
        parts.append("\n**At the cellular level**")
        for e in cell:
            parts.append(f"- **{e['name']}** acts on {e['cells']} at the {e['site']}: {e['mechanism']} (evidence {e['evidence']})")
    conf = 0.6 if (labs or sigs) else 0.4
    return {"answer": "\n".join(parts) if parts else "I don't have enough in your Vault to research this yet — add the related tests or signals.",
            "evidence_ids": list(dict.fromkeys(evidence))[:8], "confidence": conf, "medical": bool(MEDICAL_WORDS.search(question)),
            "engine": "telomy-retrieval (deep RAG)"}


def ask(question: str, chat_id: int | None = None, mode: str = "normal") -> dict:
    now = engine.now_iso()
    if not chat_id:
        chat_id = db.exec_("INSERT INTO chats (ts, title) VALUES (?,?)", (now, question[:60]))
    history = db.rows("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    db.exec_("INSERT INTO messages (chat_id, ts, role, content, meta) VALUES (?,?,?,?,?)",
             (chat_id, now, "user", question, None))
    from . import trackers
    cap = trackers.capture(question)              # anything said to Sinc can set up tracking, baselines and a plan
    if cap:
        out = {"answer": cap["answer"], "evidence_ids": [], "confidence": 0.9, "medical": cap["medical"], "engine": "telomy-trackers",
               "trackers": [{"id": t["id"], "name": t["name"], "kind": t["kind"], "new": t["new"]} for t in cap["trackers"]],
               "red_flag": cap["red_flag"], "mode": mode, "chips": [], "review_state": "none"}
        mid = db.exec_("INSERT INTO messages (chat_id, ts, role, content, meta) VALUES (?,?,?,?,?)",
                       (chat_id, engine.now_iso(), "assistant", out["answer"], db.j(out)))
        return {"chat_id": chat_id, "message_id": mid, **out}
    from . import telomy_llm, retrieval
    out = None
    deep = mode == "deep"
    if telomy_llm.available():
        # deep mode gets a broader grounding context and a be-thorough nudge; the wrapper picks the best provider
        ctx = retrieval.context(question, k=26 if deep else 18)
        sys_prompt = SYSTEM + ("\nThis is a DEEP RESEARCH request: be thorough, connect findings across labs, wearables, "
                               "trackers and genetics, explain mechanisms, and cite the person's own numbers." if deep else "")
        r = telomy_llm.ask(sys_prompt, ctx, question, history, SCHEMA, max_tokens=6000 if deep else 4000)
        if r and "_error" not in r:
            out = r
        elif r and "_error" in r:
            out = _deep_compose(question) if deep else _compose(question)
            out["notice"] = f"Answered from your Vault directly ({r['_error']})."
    if out is None:
        out = _deep_compose(question) if deep else _compose(question)
    out["medical"] = bool(out.get("medical") or MEDICAL_WORDS.search(question))
    out["mode"] = mode
    if mode == "deep":
        refs = _deep_refs(out)
        out["references"] = refs
        if refs and out.get("engine", "").startswith("telomy-retrieval"):
            out["answer"] += "\n\n**What the research says**\n" + "\n".join(
                f"- {r['finding']} _({r['citation']})_" for r in refs)
    out["review_state"] = "awaiting" if out["medical"] else "none"
    ev_index = {i["id"]: i for i in engine.list_insights(include_dismissed=True)}
    chips = []
    for e in out.get("evidence_ids", []):
        if e in ev_index:
            chips.append({"id": e, "type": "insight", "label": ev_index[e]["title"]})
        elif e in MARKERS:
            chips.append({"id": e, "type": "marker", "label": MARKERS[e][0]})
        elif e in engine.SIGNALS:
            chips.append({"id": e, "type": "signal", "label": engine.SIGNALS[e][0]})
    out["chips"] = chips
    mid = db.exec_("INSERT INTO messages (chat_id, ts, role, content, meta) VALUES (?,?,?,?,?)",
                   (chat_id, engine.now_iso(), "assistant", out["answer"], db.j(out)))
    for m in MEMORY_PAT.findall(question):
        db.exec_("INSERT INTO memories (ts, fact, source) VALUES (?,?,?)", (now, m.strip().capitalize(), "Sinc chat"))
    return {"chat_id": chat_id, "message_id": mid, **out}


# ------------------------------------------------------------------ on-device Sinc (small model on the iPhone)

SLM_SYSTEM = """You are Sinc, the health companion in the Telomy app, running on the person's iPhone.
Answer ONLY from the FACTS below: their own lab results, wearable signals, targets and the engine's findings.
Rules: first person, warm, precise; no exclamation marks, no emoji; every number must be copied exactly from FACTS
with its date or window; if FACTS lack the answer, say what is missing and how to get it; correlations are not
causes; never diagnose or prescribe, never suggest a dose; for anything medical, suggest asking their doctor.
Under 150 words. Plain English."""


def slm_context(question: str = "") -> dict:
    """Compact, line-per-fact context for a 1–2 B on-device model (it reads ~2 k tokens well, not a JSON dump).
    The phone checks every number in the model's answer against this text and falls back to /sinc/ask if one is
    not here — the grounding guard."""
    q = question.lower()
    p = engine.profile()
    age = engine.age_on()
    L = [f"Today: {engine.last_signal_day() or datetime.now().date().isoformat()}"]
    L.append("Person: " + ", ".join(x for x in [p.get("sex"), f"{age:.0f} years" if age else None,
                                                f"{p['height_cm']:.0f} cm" if p.get("height_cm") else None,
                                                f"{p['weight_kg']:.0f} kg" if p.get("weight_kg") else None,
                                                f"goal: {p['goal']}" if p.get("goal") else None] if x))
    latest = engine.latest_values()
    flagged, asked, rest = [], [], []
    for k, v in latest.items():
        spec = MARKERS.get(k)
        if not spec:
            continue
        val = v["value_num"] if v["value_num"] is not None else v["value_text"]
        line = f"Lab {spec[0]}: {val} {v['unit'] or ''}".rstrip() + f" on {v['collected_on']}"
        if v.get("ref_text"):
            line += f" (lab range {v['ref_text']})"
        if v.get("status") in ("out_of_range", "variant", "detected", "absent"):
            line += " — " + {"out_of_range": "outside the optimal range", "variant": "gene variant", "detected": "detected",
                             "absent": "absent"}[v["status"]]
        names = [spec[0].lower()] + [a for a in (spec[6] if isinstance(spec[6], list) else []) if isinstance(a, str)]
        if any(re.search(rf"\b{re.escape(n.lower())}", q) for n in names if len(n) > 2) or re.search(rf"\b{re.escape(k)}\b", q):
            asked.append(line)
        elif v.get("status") == "out_of_range":
            flagged.append(line)
        else:
            rest.append(line)
    L += asked[:10] + flagged[:15] + rest[:max(0, 20 - len(asked) - len(flagged))]
    for m, spec in engine.SIGNALS.items():
        b = engine.signal_baseline(m, days=30)
        if b:
            L.append(f"Signal {spec[0]}: 30-day mean {round(b['mean'], spec[3]) if spec[3] else round(b['mean'])} {spec[1]} ({b['n']} days)".replace("  ", " "))
    try:
        from . import whoop_day
        d = whoop_day.day()
        if d.get("ok"):
            L.append(f"WHOOP today: strain {d['strain']}, resting heart rate {d['restingHr']} bpm, {len(d['workouts'])} workouts detected")
    except Exception:  # noqa: BLE001 — no WHOOP
        pass
    try:
        from . import nutrition
        t = nutrition.targets(p.get("goal") if p.get("goal") in ("maintain", "lose") else "maintain")
        if t.get("ok"):
            L.append(f"Daily targets: {t['kcal']} kcal, protein {t['protein_g']} g, fibre {t['fibre_g']} g, carbs {t['carbs_g']} g, fat {t['fat_g']} g")
            L += [f"Lab note: {n['text']}" for n in t["labs"][:5]]
    except Exception:  # noqa: BLE001
        pass
    for i in engine.list_insights()[:8]:
        L.append(f"Finding [{i['id']}] {i['title']}: {re.sub(r'\s+', ' ', i['body'] or '')[:220]} (confidence {int(i['confidence'] * 100)}%)")
    mem = [m["fact"] for m in db.rows("SELECT fact FROM memories ORDER BY ts DESC LIMIT 5")]
    L += [f"They told me: {m}" for m in mem]
    text = "\n".join(L)
    return {"system": SLM_SYSTEM, "facts": text, "chars": len(text)}


def log_on_device(question: str, answer: str, chat_id: int | None, model: str) -> dict:
    """Keep on-device answers in the same chat history (text only; nothing else leaves the phone that wasn't already
    on the user's own server)."""
    now = engine.now_iso()
    if not chat_id:
        chat_id = db.exec_("INSERT INTO chats (ts, title) VALUES (?,?)", (now, question[:60]))
    db.exec_("INSERT INTO messages (chat_id, ts, role, content, meta) VALUES (?,?,?,?,?)", (chat_id, now, "user", question, None))
    meta = {"engine": f"{model} (on this iPhone)", "medical": bool(MEDICAL_WORDS.search(question)), "evidence_ids": []}
    meta["review_state"] = "awaiting" if meta["medical"] else "none"
    mid = db.exec_("INSERT INTO messages (chat_id, ts, role, content, meta) VALUES (?,?,?,?,?)", (chat_id, engine.now_iso(), "assistant", answer, db.j(meta)))
    return {"chat_id": chat_id, "message_id": mid, **meta}
