"""Regenerate docs/API.md (from the FastAPI OpenAPI schema) and docs/DATA_MODEL.md (from the live SQLite schema).

  backend/.venv/bin/python scripts/gen_docs.py
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.environ.setdefault("TELOMY_TODAY", "2026-10-06")

from app.main import app  # noqa: E402

spec = app.openapi()
groups: dict[str, list] = {}
for path, ops in sorted(spec["paths"].items()):
    seg = path.strip("/").split("/")[0] or "root"
    for method, op in ops.items():
        groups.setdefault(seg, []).append((method.upper(), path, (op.get("summary") or "").strip()))
lines = ["# API reference", "", "Generated from the FastAPI OpenAPI schema by `scripts/gen_docs.py` — do not edit by hand.",
         f"Interactive docs: run the backend and open `http://127.0.0.1:8787/docs`. {sum(len(v) for v in groups.values())} operations.", ""]
for seg, rows in groups.items():
    lines += [f"## /{seg}", "", "| Method | Path | Summary |", "|---|---|---|"]
    lines += [f"| {m} | `{p}` | {s} |" for m, p, s in rows] + [""]
open(os.path.join(ROOT, "docs", "API.md"), "w").write("\n".join(lines))

db = os.path.join(ROOT, "backend", "telomy.db")
if os.path.exists(db):
    con = sqlite3.connect(db)
    tables = con.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    out = ["# Data model", "", "Generated from the SQLite schema by `scripts/gen_docs.py`. JSON columns (`data`, `params`, `features`, `trace`…) hold",
           "structured payloads documented in the owning module.", ""]
    for name, sql in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        out += [f"## `{name}` ({n} seed rows)", "", "```sql", sql.strip(), "```", ""]
    open(os.path.join(ROOT, "docs", "DATA_MODEL.md"), "w").write("\n".join(out))
print("docs/API.md and docs/DATA_MODEL.md regenerated")
