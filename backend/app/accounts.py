"""Multi-user accounts — sign-up / login, and one database file per user.

Identity lives in a small shared accounts DB (users + tokens). Each user's health data lives in its own SQLite file
(`data/users/<id>.db`), created and schema-initialised on first login. Isolation is physical: no query can cross users
because each user is a separate file — the same guarantee the team gets from Supabase row-level security, simpler to
reason about, back up, and erase (delete one file = GDPR erase).

Passwords are PBKDF2-HMAC-SHA256 with a per-user salt (never stored or logged in plaintext). Tokens are random,
opaque, and map to a user; logging out deletes the token. Multi-user turns ON automatically once the first account
exists; until then the app stays in its existing single-user mode, so local dev and the current deployment are
unchanged.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager

from . import db

def _dir() -> str:
    return os.environ.get("TELOMY_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))


def accounts_db() -> str:
    return os.path.join(_dir(), "accounts.db")


def users_dir() -> str:
    return os.path.join(_dir(), "users")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT,
  pw_hash TEXT, salt TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY, user_id INTEGER, created_at REAL);
"""
_ITER = 200_000


def init():
    os.makedirs(users_dir(), exist_ok=True)
    with _acc() as c:
        c.executescript(_SCHEMA)


@contextmanager
def _acc():
    os.makedirs(_dir(), exist_ok=True)
    conn = sqlite3.connect(accounts_db(), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def enabled() -> bool:
    """Multi-user is on once at least one account exists."""
    try:
        with _acc() as c:
            return c.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None
    except sqlite3.OperationalError:
        return False


def user_db_path(user_id: int) -> str:
    return os.path.join(users_dir(), f"{user_id}.db")


def _hash(pw: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), _ITER).hex()


def _ensure_user_db(user_id: int):
    """Create + schema-init a user's own DB, running every module's init() against it (empty, no demo data)."""
    path = user_db_path(user_id)
    db.set_db(path)
    try:
        if not os.path.exists(path):
            db.init()
        from . import roles, plans, therapy, rx, summaries, voice, routine, activities, exposome, devices, band, whoop, cgm, trackers, science
        for mod in (roles, plans, therapy, rx, summaries, voice, routine, activities, exposome, devices, band, whoop, cgm, trackers, science):
            try:
                mod.init()
            except Exception:  # noqa: BLE001
                pass
    finally:
        db.set_db(None)


def signup(email: str, password: str, name: str = "") -> dict:
    email = (email or "").strip().lower()
    if "@" not in email or len(password) < 8:
        raise ValueError("Enter a valid email and a password of at least 8 characters.")
    init()
    with _acc() as c:
        if c.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise ValueError("An account with this email already exists.")
        salt = secrets.token_hex(16)
        uid = c.execute("INSERT INTO users (email, name, pw_hash, salt, created_at) VALUES (?,?,?,?,?)",
                        (email, name.strip()[:80], _hash(password, salt), salt, __import__("datetime").datetime.now().isoformat())).lastrowid
    _ensure_user_db(uid)
    return {"user_id": uid, "token": _new_token(uid), "email": email, "name": name}


def login(email: str, password: str) -> dict:
    email = (email or "").strip().lower()
    init()
    with _acc() as c:
        u = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not u or not hmac.compare_digest(_hash(password, u["salt"]), u["pw_hash"]):
        time.sleep(0.5)
        raise ValueError("Email or password is incorrect.")
    _ensure_user_db(u["id"])
    return {"user_id": u["id"], "token": _new_token(u["id"]), "email": email, "name": u["name"]}


def _new_token(user_id: int) -> str:
    tok = secrets.token_urlsafe(32)
    with _acc() as c:
        c.execute("INSERT INTO tokens (token, user_id, created_at) VALUES (?,?,?)", (tok, user_id, time.time()))
    return tok


def user_for_token(token: str) -> int | None:
    if not token:
        return None
    try:
        with _acc() as c:
            r = c.execute("SELECT user_id FROM tokens WHERE token = ?", (token,)).fetchone()
        return r["user_id"] if r else None
    except sqlite3.OperationalError:
        return None


def logout(token: str):
    with _acc() as c:
        c.execute("DELETE FROM tokens WHERE token = ?", (token,))


def migrate_single_user(email: str, password: str, name: str = "") -> dict:
    """One-time: turn the existing single-file telomy.db into the first user's database, so current data isn't lost."""
    init()
    if enabled():
        raise ValueError("Accounts already exist; nothing to migrate.")
    email = email.strip().lower()
    salt = secrets.token_hex(16)
    with _acc() as c:
        uid = c.execute("INSERT INTO users (email, name, pw_hash, salt, created_at) VALUES (?,?,?,?,?)",
                        (email, name.strip()[:80], _hash(password, salt), salt, "")).lastrowid
    dest = user_db_path(uid)
    import shutil
    for suffix in ("", "-wal", "-shm"):
        src = db.DB_PATH + suffix
        if os.path.exists(src):
            shutil.copy2(src, dest + suffix)
    if not os.path.exists(dest):
        _ensure_user_db(uid)
    return {"user_id": uid, "token": _new_token(uid), "email": email, "copied_from": db.DB_PATH}
