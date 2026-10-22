"""Staff accounts & role-based auth for the consoles — the Centre side and the Doctor side log in separately and land
in different workspaces. A staff account belongs to an org and a role:

  * clinic_admin  — doctor-side admin: full Doctor workspace + clinic config.
  * doctor        — Doctor workspace only (inbox, patients, charting, prescriptions, tasks).
  * centre_admin  — full Centre workspace + config (modules, catalog, integrations, staff).
  * centre_staff  — Centre workspace, operations only (schedule, members, check-in, orders).

A login returns a token carrying {org, role, name}; the console shows only the workspace(s) the role allows. Passwords
are PBKDF2-HMAC-SHA256; tokens are opaque. Separate from patient accounts (accounts.py) — staff never see the consumer
app, patients never see the consoles.
"""
import hashlib
import hmac
import secrets
import time

from . import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, role TEXT, name TEXT, email TEXT UNIQUE,
  pw_hash TEXT, salt TEXT, active INTEGER DEFAULT 1, created_at REAL, data TEXT);
CREATE TABLE IF NOT EXISTS staff_tokens (token TEXT PRIMARY KEY, staff_id INTEGER, created_at REAL);
"""
# Roles across four workspaces. `workspace` decides which console a login sees; `admin` grants management within it.
# `delivers` marks operational staff who deliver sessions (therapies/machines) and so accrue performance + revenue.
ROLES = {
    # platform
    "super_admin": {"workspace": "platform", "admin": True, "label": "Super admin"},
    # doctor side
    "clinic_admin": {"workspace": "doctor", "admin": True, "label": "Clinic admin"},
    "doctor": {"workspace": "doctor", "admin": False, "label": "Doctor", "delivers": True},
    # centre side
    "centre_admin": {"workspace": "centre", "admin": True, "label": "Centre admin"},
    "centre_manager": {"workspace": "centre", "admin": True, "label": "Centre manager"},
    "centre_staff": {"workspace": "centre", "admin": False, "label": "Front desk / staff"},
    "therapist": {"workspace": "centre", "admin": False, "label": "Therapist", "delivers": True},
    "operator": {"workspace": "centre", "admin": False, "label": "Machine operator", "delivers": True},
    "nurse": {"workspace": "centre", "admin": False, "label": "Nurse", "delivers": True},
    "physio": {"workspace": "centre", "admin": False, "label": "Physiotherapist", "delivers": True},
    "nutritionist": {"workspace": "centre", "admin": False, "label": "Nutritionist", "delivers": True},
    "trainer": {"workspace": "centre", "admin": False, "label": "Strength coach / trainer", "delivers": True},
}
_ITER = 200_000


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _hash(pw: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), _ITER).hex()


def create_staff(org: str, role: str, name: str, email: str, password: str, by: str = "setup", profile: dict | None = None) -> dict:
    if role not in ROLES:
        raise ValueError(f"role must be one of {sorted(ROLES)}")
    email = (email or "").strip().lower()
    if "@" not in email or len(password) < 8:
        raise ValueError("a valid email and a password of 8+ characters are required")
    init()
    if db.one("SELECT 1 AS x FROM staff WHERE email = ?", (email,)):
        raise ValueError("a staff account with this email already exists")
    salt = secrets.token_hex(16)
    data = {"by": by, **(profile or {})}
    sid = db.exec_("INSERT INTO staff (org, role, name, email, pw_hash, salt, active, created_at, data) VALUES (?,?,?,?,?,?,1,?,?)",
                   (org, role, name.strip()[:80], email, _hash(password, salt), salt, time.time(), db.j(data)))
    return {"id": sid, "org": org, "role": role, "name": name, "email": email}


def get_staff(sid: int) -> dict | None:
    r = db.one("SELECT * FROM staff WHERE id = ?", (sid,))
    if not r:
        return None
    meta = ROLES.get(r["role"], {})
    return {"id": r["id"], "org": r["org"], "role": r["role"], "label": meta.get("label", r["role"]),
            "workspace": meta.get("workspace"), "delivers": bool(meta.get("delivers")), "name": r["name"],
            "email": r["email"], "active": r["active"], "profile": {k: v for k, v in db.unj(r["data"], {}).items() if k != "by"}}


def update_profile(sid: int, name: str | None = None, profile: dict | None = None) -> dict:
    r = db.one("SELECT * FROM staff WHERE id = ?", (sid,))
    if not r:
        raise ValueError("no such staff member")
    data = db.unj(r["data"], {})
    if profile:
        data.update(profile)
    db.exec_("UPDATE staff SET name = COALESCE(?, name), data = ? WHERE id = ?",
             ((name.strip()[:80] if name else None), db.j(data), sid))
    return get_staff(sid)


def login(email: str, password: str) -> dict:
    email = (email or "").strip().lower()
    init()
    u = db.one("SELECT * FROM staff WHERE email = ? AND active = 1", (email,))
    if not u or not hmac.compare_digest(_hash(password, u["salt"]), u["pw_hash"]):
        time.sleep(0.4)
        raise ValueError("Email or password is incorrect.")
    tok = secrets.token_urlsafe(32)
    db.exec_("INSERT INTO staff_tokens (token, staff_id, created_at) VALUES (?,?,?)", (tok, u["id"], time.time()))
    r = ROLES[u["role"]]
    return {"token": tok, "org": u["org"], "role": u["role"], "name": u["name"], "workspace": r["workspace"], "admin": r["admin"],
            "label": r["label"]}


_TOKEN_TTL = 30 * 86400          # staff console sessions expire after 30 days (L1 — tokens no longer live forever)


def whoami(token: str) -> dict | None:
    if not token:
        return None
    t = db.one("SELECT * FROM staff_tokens WHERE token = ?", (token,))
    if not t:
        return None
    if time.time() - (t["created_at"] or 0) > _TOKEN_TTL:        # expired — revoke and reject
        db.exec_("DELETE FROM staff_tokens WHERE token = ?", (token,))
        return None
    u = db.one("SELECT * FROM staff WHERE id = ? AND active = 1", (t["staff_id"],))
    if not u:
        return None
    r = ROLES[u["role"]]
    return {"staff_id": u["id"], "org": u["org"], "role": u["role"], "name": u["name"], "email": u["email"],
            "workspace": r["workspace"], "admin": r["admin"], "label": r["label"]}


def logout(token: str):
    db.exec_("DELETE FROM staff_tokens WHERE token = ?", (token,))


def list_staff(org: str, role: str | None = None) -> list[dict]:
    q = "SELECT * FROM staff WHERE org = ?"
    args: list = [org]
    if role:
        q += " AND role = ?"; args.append(role)
    out = []
    for r in db.rows(q + " ORDER BY role, name", tuple(args)):
        meta = ROLES.get(r["role"], {})
        prof = {k: v for k, v in db.unj(r["data"], {}).items() if k != "by"}
        out.append({"id": r["id"], "name": r["name"], "email": r["email"], "role": r["role"],
                    "label": meta.get("label", r["role"]), "workspace": meta.get("workspace"),
                    "delivers": bool(meta.get("delivers")), "active": r["active"], "profile": prof})
    return out


def all_staff() -> list[dict]:
    """Platform-wide — every staff account across every org (super-admin view)."""
    return [{"id": r["id"], "name": r["name"], "email": r["email"], "role": r["role"], "org": r["org"],
             "label": ROLES.get(r["role"], {}).get("label", r["role"]), "active": r["active"]}
            for r in db.rows("SELECT * FROM staff ORDER BY org, role, name")]


def set_active(sid: int, active: bool):
    db.exec_("UPDATE staff SET active = ? WHERE id = ?", (1 if active else 0, sid))


def any_staff() -> bool:
    try:
        return db.one("SELECT 1 AS x FROM staff LIMIT 1") is not None
    except Exception:  # noqa: BLE001
        return False
