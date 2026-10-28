"""Knowledge base retriever — the query side of the clinical knowledge engine (Track A).

A read-only SQLite **FTS5** index (`knowledge.db`) of graded, cited chunks is built on the ingest box by
`ingest/build_kb.py` and shipped to the query box. This module searches it with BM25, re-ranks by evidence grade,
and returns chunks ready to ground an answer. It never writes. When no KB is present, `available()` is False and the
caller (clinevidence) falls back to live PubMed.

Schema (see ingest/build_kb.py):
  docs(doc_id PK, source, title, url, year, pub_type, grade, grade_label, license, region)
  chunks  FTS5(doc_id UNINDEXED, section, body, tokenize='porter unicode61')
  meta(key, value)
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.join(_HERE, "..", "data", "kb", "knowledge.db")
DB_PATH = os.environ.get("TELOMY_KB_PATH", os.path.normpath(_DEFAULT))

_GRADE_WEIGHT = {"A": 1.0, "B": 0.85, "C": 0.7, "D": 0.55}
_local = threading.local()
_STOP = set("the a an and or of to in on for with without is are was were be been being this that these those by as at "
            "from into than then there their them they it its what why how when which who does did do can could should "
            "would will just also more most less my your our vs versus use used using patient patients".split())


def available() -> bool:
    return os.path.exists(DB_PATH)


def _conn() -> sqlite3.Connection | None:
    if not available():
        return None
    c = getattr(_local, "conn", None)
    if c is None:
        # read-only, shared across threads of this worker; FTS5 reads are safe concurrently
        c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
        c.row_factory = sqlite3.Row
        _local.conn = c
    return c


def _fts_query(q: str) -> str:
    """Turn a natural-language clinical question into a safe FTS5 MATCH expression (OR of quoted content words)."""
    words = [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", q.lower()) if len(w) > 2 and w not in _STOP]
    words = list(dict.fromkeys(words))[:12]
    return " OR ".join(f'"{w}"' for w in words)


def stats() -> dict:
    c = _conn()
    if not c:
        return {"available": False}
    try:
        docs = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        chunks = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        built = c.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        return {"available": True, "docs": docs, "chunks": chunks, "built_at": built[0] if built else None, "path": DB_PATH}
    except sqlite3.Error as e:
        return {"available": True, "error": str(e)}


def search(query: str, k: int = 8) -> list[dict]:
    """Top-k graded chunks for a query: BM25 recall, then re-rank by (match strength × evidence-grade weight)."""
    c = _conn()
    if not c or not query.strip():
        return []
    m = _fts_query(query)
    if not m:
        return []
    try:
        rows = c.execute(
            """SELECT c.doc_id, c.section, c.body, bm25(chunks) AS rank,
                      d.title, d.url, d.year, d.grade, d.grade_label, d.source, d.pub_type
               FROM chunks c JOIN docs d ON d.doc_id = c.doc_id
               WHERE chunks MATCH ? ORDER BY rank LIMIT ?""",
            (m, max(k * 4, 24)),
        ).fetchall()
    except sqlite3.Error:
        return []
    out = []
    for r in rows:
        # SQLite bm25() is smaller = better; flip to a positive relevance, then weight by grade
        rel = -float(r["rank"])
        weight = _GRADE_WEIGHT.get(r["grade"], 0.55)
        out.append({
            "doc_id": r["doc_id"], "section": r["section"], "body": r["body"],
            "title": r["title"], "url": r["url"], "year": r["year"], "source": r["source"],
            "grade": r["grade"], "grade_label": r["grade_label"], "pub_type": r["pub_type"],
            "_score": rel * weight,
        })
    out.sort(key=lambda x: x["_score"], reverse=True)
    # one chunk per document (dedupe), keep the best
    seen, uniq = set(), []
    for x in out:
        if x["doc_id"] in seen:
            continue
        seen.add(x["doc_id"])
        uniq.append(x)
        if len(uniq) >= k:
            break
    return uniq
