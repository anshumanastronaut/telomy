"""SQLite storage. One file, created on first use. JSON columns hold structured payloads."""
import json
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("TELOMY_DB", os.path.join(os.path.dirname(__file__), "..", "telomy.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, panel TEXT, collected_on TEXT, source TEXT,
  filename TEXT, is_test_data INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
  marker_id TEXT, value_num REAL, value_text TEXT, unit TEXT, ref_low REAL, ref_high REAL, ref_text TEXT,
  flag TEXT, status TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS ix_results_marker ON results(marker_id);
CREATE TABLE IF NOT EXISTS signals (
  day TEXT, metric TEXT, value REAL, source TEXT, PRIMARY KEY (day, metric));
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, label TEXT, severity INTEGER,
  data TEXT, source TEXT DEFAULT 'manual');
CREATE INDEX IF NOT EXISTS ix_events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS meals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, name TEXT, analysis TEXT);
CREATE TABLE IF NOT EXISTS insights (
  id TEXT PRIMARY KEY, created_at TEXT, kind TEXT, title TEXT, body TEXT, confidence REAL,
  evidence TEXT, receipts TEXT, review_state TEXT, medical INTEGER DEFAULT 0, dismissed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS review_thread (
  id INTEGER PRIMARY KEY AUTOINCREMENT, insight_id TEXT, ts TEXT, author TEXT, action TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS consents (purpose TEXT PRIMARY KEY, granted INTEGER, updated_at TEXT);
CREATE TABLE IF NOT EXISTS consent_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, purpose TEXT, granted INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS studies (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, intervention TEXT, outcome TEXT, design TEXT,
  start_day TEXT, period_days INTEGER, status TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS protocols (id TEXT PRIMARY KEY, data TEXT, active INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS checklist (day TEXT, item_id TEXT, done INTEGER, PRIMARY KEY (day, item_id));
CREATE TABLE IF NOT EXISTS clinicians (id TEXT PRIMARY KEY, data TEXT);
CREATE TABLE IF NOT EXISTS appointments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, clinician_id TEXT, ts TEXT, kind TEXT, status TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS shares (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, relation TEXT, scopes TEXT, expires_on TEXT,
  status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS access_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, who TEXT, what TEXT);
CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, fact TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, title TEXT);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, ts TEXT, role TEXT, content TEXT, meta TEXT);
CREATE TABLE IF NOT EXISTS sessions_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, minutes REAL, data TEXT);
CREATE TABLE IF NOT EXISTS imaging (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT);
CREATE TABLE IF NOT EXISTS medications (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dose TEXT, frequency TEXT, times TEXT, reason TEXT,
  prescriber TEXT, start_day TEXT, active INTEGER DEFAULT 1, source TEXT);
CREATE TABLE IF NOT EXISTS med_doses (id INTEGER PRIMARY KEY AUTOINCREMENT, med_id INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS notif_read (key TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, day TEXT, filename TEXT, summary TEXT, data TEXT, created_at TEXT);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def tx():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init(reset: bool = False):
    if reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with tx() as c:
        c.executescript(SCHEMA)


def rows(sql: str, args=()) -> list[dict]:
    with tx() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql: str, args=()) -> dict | None:
    r = rows(sql, args)
    return r[0] if r else None


def exec_(sql: str, args=()) -> int:
    with tx() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def unj(s, default=None):
    return json.loads(s) if s else default
