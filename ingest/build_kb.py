#!/usr/bin/env python3
"""Build the Telomy knowledge base (SQLite FTS5) — the ingest side of the clinical knowledge engine (Track A).

Runs on the ingest box (or locally for a seed). Pulls graded, cited chunks from sources and writes `knowledge.db`,
which the backend queries read-only via `app/kb.py`. Milestone 1 seeds from PubMed (reusing the backend's graded
E-utilities client) plus any local guideline/text files; A2 adds PMC-OA / DailyMed / India-guideline loaders.

Usage (from repo root, backend venv active):
    python ingest/build_kb.py --seed                      # seed from the built-in clinical topic list
    python ingest/build_kb.py --queries "sepsis" "afib"   # ingest specific topics
    python ingest/build_kb.py --text path/to/guideline.txt --title "USPSTF: ..." --grade A --source uspstf
    python ingest/build_kb.py --stats

Every chunk carries: source, title, url, year, pub_type, grade(A-D), license, region — the metadata that makes this
a *clinical* index (we rank partly by grade and can filter by license/region at query time).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

# import the backend package so we reuse the graded PubMed client (no duplicate retrieval/grading logic)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

DB_PATH = os.environ.get("TELOMY_KB_PATH", os.path.join(_ROOT, "backend", "data", "kb", "knowledge.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
  doc_id TEXT PRIMARY KEY, source TEXT, title TEXT, url TEXT, year TEXT,
  pub_type TEXT, grade TEXT, grade_label TEXT, license TEXT, region TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
  doc_id UNINDEXED, section, body, tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""

# A broad starter set of point-of-care topics (expand freely; A2 replaces this with bulk corpora).
SEED_TOPICS = [
    "atrial fibrillation anticoagulation stroke prevention", "heart failure reduced ejection fraction guideline",
    "type 2 diabetes first line pharmacotherapy", "hypertension management guideline adults",
    "community acquired pneumonia antibiotic treatment", "sepsis early management bundle",
    "acute coronary syndrome management", "statin primary prevention cardiovascular disease",
    "chronic kidney disease management SGLT2", "COPD exacerbation management",
    "asthma stepwise management adults", "venous thromboembolism treatment anticoagulation",
    "stroke acute ischemic thrombolysis", "hypothyroidism levothyroxine dosing",
    "dyslipidemia LDL target high risk", "upper gastrointestinal bleeding management",
    "diabetic ketoacidosis management", "hyponatremia evaluation treatment",
    "urinary tract infection treatment guideline", "depression first line pharmacotherapy",
    "anemia iron deficiency evaluation", "osteoporosis treatment postmenopausal",
    "gout acute management urate lowering", "migraine prophylaxis treatment",
    "GLP-1 receptor agonist weight management", "obstructive sleep apnea diagnosis treatment",
]


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.executescript(SCHEMA)
    return c


def add_doc(c: sqlite3.Connection, doc: dict, chunks: list[dict]) -> bool:
    """Insert a document + its chunks. Returns True if newly added."""
    if c.execute("SELECT 1 FROM docs WHERE doc_id=?", (doc["doc_id"],)).fetchone():
        return False
    c.execute("INSERT INTO docs(doc_id,source,title,url,year,pub_type,grade,grade_label,license,region) "
              "VALUES(:doc_id,:source,:title,:url,:year,:pub_type,:grade,:grade_label,:license,:region)", doc)
    for ch in chunks:
        c.execute("INSERT INTO chunks(doc_id,section,body) VALUES(?,?,?)", (doc["doc_id"], ch.get("section", ""), ch["body"]))
    return True


def ingest_pubmed(c: sqlite3.Connection, queries: list[str], per: int = 8) -> int:
    from app import clinevidence  # reuse the graded retriever
    added = 0
    for q in queries:
        arts = clinevidence.search(q, per)
        for a in arts:
            if a.get("_error") or not a.get("abstract"):
                continue
            doc = {
                "doc_id": f"pmid:{a['pmid']}", "source": "pubmed", "title": a["title"], "url": a["url"],
                "year": a.get("year", ""), "pub_type": "; ".join(a.get("pub_types", []))[:200],
                "grade": a["grade"], "grade_label": a["grade_label"], "license": "metadata-free", "region": "global",
            }
            if add_doc(c, doc, [{"section": "abstract", "body": f"{a['title']}. {a['abstract']}"}]):
                added += 1
        time.sleep(0.4)  # be polite to NCBI
        print(f"  · {q[:48]:48s} (+{added} total)")
    return added


def ingest_text(c: sqlite3.Connection, path: str, title: str, grade: str, source: str,
                url: str = "", region: str = "global", license: str = "public-domain") -> int:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()
    if not text:
        return 0
    # naive paragraph chunking (A2 upgrades to section-aware ~512-800 token chunks)
    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 120]
    glabel = {"A": "Strong", "B": "Moderate", "C": "Limited", "D": "Weak"}.get(grade, "")
    doc = {"doc_id": f"{source}:{os.path.basename(path)}", "source": source, "title": title, "url": url,
           "year": str(time.gmtime().tm_year), "pub_type": "guideline/text", "grade": grade,
           "grade_label": glabel, "license": license, "region": region}
    return 1 if add_doc(c, doc, [{"section": f"p{i+1}", "body": p} for i, p in enumerate(paras)]) else 0


def finish(c: sqlite3.Connection):
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('built_at',?)",
              (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),))
    c.commit()
    d = c.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    ch = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"knowledge.db: {d} docs, {ch} chunks → {DB_PATH}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true", help="ingest the built-in clinical topic list from PubMed")
    ap.add_argument("--queries", nargs="*", help="PubMed topics to ingest")
    ap.add_argument("--per", type=int, default=8, help="articles per query")
    ap.add_argument("--text", help="a local guideline/text file to ingest")
    ap.add_argument("--title", default="")
    ap.add_argument("--grade", default="A")
    ap.add_argument("--source", default="guideline")
    ap.add_argument("--url", default="")
    ap.add_argument("--region", default="global")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    c = connect()
    if args.stats:
        print(c.execute("SELECT (SELECT COUNT(*) FROM docs), (SELECT COUNT(*) FROM chunks)").fetchone())
        return
    if args.text:
        n = ingest_text(c, args.text, args.title or os.path.basename(args.text), args.grade, args.source, args.url, args.region)
        print(f"ingested text: +{n} doc")
    topics = (SEED_TOPICS if args.seed else []) + (args.queries or [])
    if topics:
        print(f"ingesting {len(topics)} PubMed topics…")
        ingest_pubmed(c, topics, args.per)
    finish(c)


if __name__ == "__main__":
    main()
