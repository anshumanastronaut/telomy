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


def ask(question: str, chat_id: int | None = None, mode: str = "normal") -> dict:
    now = engine.now_iso()
    if not chat_id:
        chat_id = db.exec_("INSERT INTO chats (ts, title) VALUES (?,?)", (now, question[:60]))
    history = db.rows("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    db.exec_("INSERT INTO messages (chat_id, ts, role, content, meta) VALUES (?,?,?,?,?)",
             (chat_id, now, "user", question, None))
    try:
        out = _ask_claude(question, history) if _claude_available() else _compose(question)
    except Exception as exc:  # network/API problems must be visible, never silent
        out = _compose(question)
        out["notice"] = f"I couldn't reach the language model ({type(exc).__name__}); this answer comes from your Vault directly."
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
