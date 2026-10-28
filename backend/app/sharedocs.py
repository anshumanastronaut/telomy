"""Doctor → patient document sharing, with the patient's consent.

A clinician attaches a report, scan or image to a patient from the Doctor workspace; it lands in the patient's own
Vault as a PENDING shared document and raises a notification. The patient reviews it and ACCEPTS (it's kept in their
records) or REJECTS it. Nothing enters the patient's account without their confirmation. Rows live in the patient's
own per-user DB (we're bound to it when these run), so one patient never sees another's shared files.
"""
from __future__ import annotations

from . import db, engine


def _ensure():
    db.exec_("""CREATE TABLE IF NOT EXISTS shared_documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, from_name TEXT, from_org TEXT,
        title TEXT, kind TEXT, media_type TEXT, data TEXT, note TEXT, status TEXT DEFAULT 'pending')""")


def add(from_name: str, from_org: str, title: str, kind: str, media_type: str | None, data: str, note: str = "") -> int:
    _ensure()
    return db.exec_(
        "INSERT INTO shared_documents(ts,from_name,from_org,title,kind,media_type,data,note,status) "
        "VALUES(?,?,?,?,?,?,?,?,'pending')",
        (engine.now_iso(), from_name, from_org, title[:160], kind, media_type, data, note[:500]))


def listing() -> list[dict]:
    _ensure()
    rows = db.rows("SELECT id, ts, from_name, from_org, title, kind, media_type, note, status, "
                   "length(data) AS bytes FROM shared_documents ORDER BY (status='pending') DESC, ts DESC")
    return [dict(r) for r in rows]


def file(sid: int) -> dict | None:
    _ensure()
    rows = db.rows("SELECT media_type, data, title, kind FROM shared_documents WHERE id=?", (sid,))
    return dict(rows[0]) if rows else None


def set_status(sid: int, status: str) -> bool:
    _ensure()
    db.exec_("UPDATE shared_documents SET status=? WHERE id=?", (status, sid))
    return True


def pending() -> list[dict]:
    _ensure()
    return [dict(r) for r in db.rows(
        "SELECT id, from_name, title, kind, ts FROM shared_documents WHERE status='pending' ORDER BY ts DESC")]
