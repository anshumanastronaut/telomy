"""Goals — what a member/patient (or their doctor/coach) is working toward, tracked against their real data. A goal can
be free-text ("feel more energetic") or tied to a measurable target (a signal like weight/hrv/vo2max or a lab marker
like ldl/hba1c); progress is read from the Vault so it updates itself. Used on both the centre and doctor apps.
"""
import time
from datetime import date

from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT, owner_kind TEXT, owner_id INTEGER,
  title TEXT, category TEXT, metric TEXT, metric_kind TEXT, baseline REAL, target REAL, direction TEXT,
  deadline TEXT, status TEXT DEFAULT 'active', set_by TEXT, created_at REAL, data TEXT);
CREATE INDEX IF NOT EXISTS ix_goals ON goals(org, owner_kind, owner_id, status);
"""


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def add_goal(org: str, title: str, owner_kind: str = "member", owner_id: int | None = None, category: str = "",
             metric: str | None = None, target: float | None = None, deadline: str | None = None,
             set_by: str = "", data: dict | None = None) -> dict:
    if not title.strip():
        raise ValueError("title is required")
    metric_kind, baseline, direction = None, None, None
    if metric:
        if metric in engine.SIGNALS:
            metric_kind = "signal"; direction = engine.SIGNALS[metric][2]
            b = engine.signal_baseline(metric, days=30); baseline = b["mean"] if b else None
        else:
            from .catalog import MARKERS
            if metric in MARKERS:
                metric_kind = "marker"; direction = MARKERS[metric][5]
                r = engine.latest_values().get(metric); baseline = r["value_num"] if r else None
    gid = db.exec_("""INSERT INTO goals (org, owner_kind, owner_id, title, category, metric, metric_kind, baseline, target,
                      direction, deadline, status, set_by, created_at, data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (org, owner_kind, owner_id, title.strip()[:160], category, metric, metric_kind, baseline, target,
                    direction, deadline, "active", set_by[:80], time.time(), db.j(data or {})))
    return goal(gid)


def _progress(g: dict) -> dict:
    """Current value from the Vault + a 0-100 progress toward the target."""
    if not g["metric"]:
        return {"current": None, "pct": None}
    cur = None
    if g["metric_kind"] == "signal":
        b = engine.signal_baseline(g["metric"], days=14); cur = b["mean"] if b else None
    elif g["metric_kind"] == "marker":
        r = engine.latest_values().get(g["metric"]); cur = r["value_num"] if r else None
    if cur is None or g["target"] is None or g["baseline"] is None:
        return {"current": cur, "pct": None}
    span = g["target"] - g["baseline"]
    pct = 100.0 if span == 0 else max(0, min(100, round(100 * (cur - g["baseline"]) / span)))
    return {"current": round(cur, 2), "pct": pct}


def goal(gid: int) -> dict | None:
    r = db.one("SELECT * FROM goals WHERE id = ?", (gid,))
    if not r:
        return None
    return {**r, "data": db.unj(r["data"], {}), **_progress(r)}


def list_goals(org: str, owner_kind: str | None = None, owner_id: int | None = None, status: str = "active") -> list[dict]:
    q = "SELECT id FROM goals WHERE org = ?"
    args: list = [org]
    if owner_kind:
        q += " AND owner_kind = ?"; args.append(owner_kind)
    if owner_id is not None:
        q += " AND owner_id = ?"; args.append(owner_id)
    if status != "all":
        q += " AND status = ?"; args.append(status)
    return [goal(r["id"]) for r in db.rows(q + " ORDER BY created_at DESC", tuple(args))]


def update_goal(gid: int, status: str | None = None, target: float | None = None, deadline: str | None = None) -> dict:
    g = db.one("SELECT * FROM goals WHERE id = ?", (gid,))
    if not g:
        raise ValueError("no such goal")
    db.exec_("UPDATE goals SET status = COALESCE(?, status), target = COALESCE(?, target), deadline = COALESCE(?, deadline) WHERE id = ?",
             (status, target, deadline, gid))
    return goal(gid)
