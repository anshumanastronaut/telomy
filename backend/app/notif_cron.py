"""Notification delivery cron (NOTIFICATIONS.md Part E.1 — generation/delivery by cron, not a daemon).

Drains each account's notification outbox through the credential-gated adapters and runs the critical-value
escalation sweep. Designed to be invoked periodically from system cron (same mechanism as the existing backup /
keepalive jobs), so the single uvicorn worker is never blocked by delivery:

    */2 * * * *  cd /opt/telomy/backend && .venv/bin/python -m app.notif_cron

Single-user / local dev: runs against the default DB. Multi-user: iterates every account's per-user DB with the
same context-var DB switch the request path uses.
"""
import sys

from . import config  # noqa: F401  (loads backend/.env so provider creds are visible to the senders)
from . import accounts as acctmod, db, notifs


def _run_one() -> dict:
    db.init()   # ensure the notification tables exist (migrates DBs created before this feature, idempotent)
    drained = notifs.drain_outbox(limit=200)
    escalated = notifs.escalate(older_than_min=30)
    return {**drained, **escalated}


def run() -> dict:
    total = {"sent": 0, "skipped": 0, "errored": 0, "escalated": 0}
    uids = acctmod.user_ids()
    if not uids:                      # single-user / local: the default DB
        r = _run_one()
        for k in total:
            total[k] += r.get(k, 0)
        return total
    for uid in uids:
        db.set_db(acctmod.user_db_path(uid))
        try:
            r = _run_one()
            for k in total:
                total[k] += r.get(k, 0)
        except Exception as exc:  # noqa: BLE001  — one bad DB must not stop the batch
            print(f"[notif_cron] user {uid}: {type(exc).__name__}: {exc}", file=sys.stderr)
        finally:
            db.set_db(None)
    return total


if __name__ == "__main__":
    print(run())
