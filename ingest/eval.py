#!/usr/bin/env python3
"""Clinical-engine evaluation harness (Track A3) — measure accuracy before trusting the engine.

Pulls a sample of an open medical-QA benchmark (MedMCQA — India AIIMS/NEET-PG style; or PubMedQA) from the
HuggingFace datasets-server REST API (free, no key), then scores our stack on it:
  · answer accuracy  — needs an LLM provider (Claude via telomy_llm); optional RAG grounding from the local KB.
  · retrieval coverage — always available: avg KB chunks retrieved + mean top evidence grade per question.

Usage (from backend/, venv active):
    python ../ingest/eval.py --dataset medmcqa --n 30 --rag
    python ../ingest/eval.py --dataset pubmedqa --n 30
    python ../ingest/eval.py --dataset medmcqa --n 30 --retrieval-only   # no LLM, coverage only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

DATASETS = {
    "medmcqa": {"dataset": "openlifescienceai/medmcqa", "config": "default", "split": "validation", "kind": "mcq"},
    "pubmedqa": {"dataset": "qiaojin/PubMedQA", "config": "pqa_labeled", "split": "train", "kind": "yesno"},
}
_GRADE_RANK = {"A": 3, "B": 2, "C": 1, "D": 0}


def _rows(ds: dict, n: int) -> list[dict]:
    url = ("https://datasets-server.huggingface.co/rows?"
           + urllib.parse.urlencode({"dataset": ds["dataset"], "config": ds["config"], "split": ds["split"], "offset": 0, "length": min(n, 100)}))
    req = urllib.request.Request(url, headers={"User-Agent": "telomy-eval/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return [x["row"] for x in json.loads(r.read()).get("rows", [])][:n]


def _kb_context(question: str, k: int = 5):
    from app import kb
    chunks = kb.search(question, k) if kb.available() else []
    ctx = "\n\n".join(f"[{i+1}] {c['title']} ({c['grade']}): {c['body'][:500]}" for i, c in enumerate(chunks))
    top_grade = max((_GRADE_RANK.get(c["grade"], 0) for c in chunks), default=-1)
    return ctx, len(chunks), top_grade


def _ask_letter(question: str, options: str, ctx: str) -> str | None:
    from app import telomy_llm
    if not telomy_llm.provider():
        return None
    sys_p = ("You are a medical exam assistant. Choose the single best answer. Use the CONTEXT if helpful. "
             "Reply with ONLY a JSON object: {\"answer\": \"A\"} (one letter).")
    out = telomy_llm.ask(sys_p, ctx or "(no context)", f"{question}\n\nOptions:\n{options}", [], {"type": "object"},
                         max_tokens=200, skip_guard=True)
    if not out or "_error" in out:
        return None
    m = re.search(r"[A-E]", str(out.get("answer", "")).upper())
    return m.group(0) if m else None


def run(name: str, n: int, rag: bool, retrieval_only: bool):
    ds = DATASETS[name]
    rows = _rows(ds, n)
    print(f"{name}: {len(rows)} questions (split={ds['split']}, rag={rag and not retrieval_only})")
    correct = answered = cov_sum = grade_sum = 0
    for r in rows:
        if ds["kind"] == "mcq":
            q = r.get("question", "")
            opts = {"A": r.get("opa", ""), "B": r.get("opb", ""), "C": r.get("opc", ""), "D": r.get("opd", "")}
            gold = "ABCD"[int(r.get("cop", 0))]
            opt_text = "\n".join(f"{k}. {v}" for k, v in opts.items())
        else:  # pubmedqa yes/no/maybe
            q = r.get("question", "")
            opts = {"A": "yes", "B": "no", "C": "maybe"}
            gold = {"yes": "A", "no": "B", "maybe": "C"}.get(str(r.get("final_decision", "")).lower(), "A")
            opt_text = "A. yes\nB. no\nC. maybe"
        ctx, cov, top = _kb_context(q) if (rag or retrieval_only) else ("", 0, -1)
        cov_sum += cov
        grade_sum += top if top >= 0 else 0
        if retrieval_only:
            continue
        pred = _ask_letter(q, opt_text, ctx if rag else "")
        if pred is None:
            continue
        answered += 1
        correct += (pred == gold)

    print(f"  retrieval coverage: {cov_sum/max(1,len(rows)):.1f} chunks/question"
          + (f", mean top grade rank {grade_sum/max(1,len(rows)):.2f}" if (rag or retrieval_only) else ""))
    if not retrieval_only and answered:
        print(f"  accuracy: {correct}/{answered} = {100*correct/answered:.1f}%")
    elif not retrieval_only:
        print("  accuracy: n/a (no LLM provider configured — set ANTHROPIC_API_KEY to score answers)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=list(DATASETS), default="medmcqa")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--rag", action="store_true", help="ground answers in the local KB")
    ap.add_argument("--retrieval-only", action="store_true", help="measure KB coverage only (no LLM)")
    a = ap.parse_args()
    run(a.dataset, a.n, a.rag, a.retrieval_only)


if __name__ == "__main__":
    main()
