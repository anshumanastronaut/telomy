"""Doctor / clinic operations — a patient roster, clinical charting from customisable note templates, a task inbox, and
links to prescriptions (rx.py) and the care-review queue. Modular and configurable: note templates come from the
platform `note_template` catalog, every note and patient carries the org's custom fields, and the doctor shapes their
own templates (SOAP or anything) without code — the pattern the best EHRs use (DrChrono/Jane form builders, ModMed-style
per-doctor templates).
"""
import time
from datetime import date, datetime

from . import db, platform

SCHEMA = """
CREATE TABLE IF NOT EXISTS cl_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, patient_id INTEGER, author TEXT,
  ts TEXT, template_id INTEGER, title TEXT, content TEXT, fields TEXT, signed INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_cl_notes ON cl_notes(patient_id, ts);
CREATE TABLE IF NOT EXISTS cl_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, patient_id INTEGER, assignee TEXT,
  text TEXT, due TEXT, priority INTEGER DEFAULT 1, status TEXT DEFAULT 'open', created_at REAL);
"""
# A default SOAP template seeded for any org that has none, so charting works out of the box.
SOAP = {"sections": [{"title": "Subjective", "key": "s", "type": "textarea"}, {"title": "Objective", "key": "o", "type": "textarea"},
                     {"title": "Assessment", "key": "a", "type": "textarea"}, {"title": "Plan", "key": "p", "type": "textarea"}]}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def templates(org: str = "default") -> list[dict]:
    t = platform.list_catalog(org, "note_template")
    if not t:
        platform.add_catalog(org, "note_template", "SOAP note", SOAP, key="soap")
        t = platform.list_catalog(org, "note_template")
    return t


# ---- clinical notes ---------------------------------------------------------------------------------------------

def add_note(org: str, patient_id: int, author: str, template_id: int | None = None, title: str = "",
             content: dict | None = None, fields: dict | None = None) -> dict:
    vals = platform.validate_values(org, "clinical_note", fields or {})
    nid = db.exec_("INSERT INTO cl_notes (org, patient_id, author, ts, template_id, title, content, fields, signed) VALUES (?,?,?,?,?,?,?,?,0)",
                   (org, patient_id, author[:80], datetime.now().isoformat(), template_id, title[:120], db.j(content or {}), db.j(vals)))
    return note(nid)


def note(nid: int) -> dict | None:
    r = db.one("SELECT * FROM cl_notes WHERE id = ?", (nid,))
    return {**r, "content": db.unj(r["content"], {}), "fields": db.unj(r["fields"], {})} if r else None


def notes_for(patient_id: int) -> list[dict]:
    return [note(r["id"]) for r in db.rows("SELECT id FROM cl_notes WHERE patient_id = ? ORDER BY ts DESC", (patient_id,))]


def sign(nid: int, by: str) -> dict:
    db.exec_("UPDATE cl_notes SET signed = 1, author = COALESCE(author, ?) WHERE id = ?", (by, nid))
    return note(nid)


# ---- tasks / inbox ----------------------------------------------------------------------------------------------

def add_task(org: str, text: str, patient_id: int | None = None, assignee: str = "", due: str | None = None, priority: int = 1) -> dict:
    if not text.strip():
        raise ValueError("task text is required")
    tid = db.exec_("INSERT INTO cl_tasks (org, patient_id, assignee, text, due, priority, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   (org, patient_id, assignee[:80], text.strip()[:300], due, max(1, min(3, priority)), "open", time.time()))
    return db.one("SELECT * FROM cl_tasks WHERE id = ?", (tid,))


def tasks(org: str = "default", status: str = "open") -> list[dict]:
    return db.rows("SELECT * FROM cl_tasks WHERE org = ? AND (? = 'all' OR status = ?) ORDER BY priority DESC, due IS NULL, due", (org, status, status))


def complete_task(tid: int) -> dict:
    db.exec_("UPDATE cl_tasks SET status = 'done' WHERE id = ?", (tid,))
    return db.one("SELECT * FROM cl_tasks WHERE id = ?", (tid,))


# ---- the doctor's day -------------------------------------------------------------------------------------------

def inbox(org: str = "default", doctor_id: int = 2) -> dict:
    """One screen for a doctor: patients needing attention, open tasks, the care-review queue, today's consults."""
    from . import roles
    try:
        patients = roles.doctor_patients(doctor_id)
    except Exception:  # noqa: BLE001
        patients = []
    care = []
    try:
        care = [i for i in db.rows("SELECT * FROM insights WHERE review_state = 'awaiting' ORDER BY created_at DESC LIMIT 20")]
    except Exception:  # noqa: BLE001
        pass
    return {"org": org, "doctor_id": doctor_id, "patients": patients[:20], "open_tasks": tasks(org, "open")[:20],
            "care_queue": [{"id": c["id"], "title": c["title"]} for c in care], "templates": templates(org)}
