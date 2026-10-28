"""Stored notification layer + delivery outbox (Phase 0 of research/intel/NOTIFICATIONS.md).

Replaces the compute-on-read-only model with durable, timestamped rows that carry priority, channels, read and
acknowledgement state, so the same event can be shown in-app *and* queued for push/SMS/WhatsApp/email later.

Design for the fragile single-worker box (NOTIFICATIONS.md Part E.1):
  • add()  — writes a notification row, idempotent on dedup_key, and enqueues one outbox row per out-of-app channel.
  • the OUTBOX is drained by a cron (Phase 1); until a real sender exists rows simply stay 'pending' — harmless.
  • the CRITICAL path (U4/D1/C1) is written inline here on ingest; a cron escalation sweep (Phase 1) promotes
    unacknowledged critical alerts. `pending_critical_unacked()` is that sweep's query.

Safety posture (agreed): Telomy *routes to a clinician*, it does not *assert* criticality to the patient. The
patient-facing critical copy below never contains the dangerous number; the clinical value is carried in `data`
for the (Phase-1) clinician delivery path only.
"""
from datetime import datetime

from . import db, criticals
from .catalog import MARKERS

# Default channels per priority (NOTIFICATIONS.md Part C global defaults). 'in_app' is always implied and never
# enqueued to the outbox (it's served straight from the stored row).
CHANNELS = {
    "critical": ["in_app", "push", "sms", "whatsapp"],
    "high":     ["in_app", "push"],
    "normal":   ["in_app", "push"],
    "low":      ["in_app"],
}
_OUTBOX_CHANNELS = {"push", "sms", "whatsapp", "email"}
# Categories that ignore per-category prefs and quiet hours entirely (NOTIFICATIONS.md Part C global defaults).
_ALWAYS_ON = {"otp", "security"}
_INTRUSIVE = {"push", "sms", "whatsapp"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _in_quiet_now() -> bool:
    """True if the current local time (user's tz, default IST) is inside the quiet window."""
    try:
        from zoneinfo import ZoneInfo
        s = db.one("SELECT * FROM notif_settings WHERE id = 1") or {}
        tz = ZoneInfo(s.get("tz") or "Asia/Kolkata")
        now = datetime.now(tz).strftime("%H:%M")
        qs, qe = (s.get("quiet_start") or "21:00"), (s.get("quiet_end") or "09:00")
        return (qs <= now < qe) if qs <= qe else (now >= qs or now < qe)  # qs>qe → window crosses midnight
    except Exception:
        return False


def _effective_channels(category: str | None, priority: str, channels: list[str]) -> list[str]:
    """Apply per-category channel prefs and quiet hours. Critical and OTP/security always deliver on every channel."""
    if priority == "critical" or (category in _ALWAYS_ON):
        return channels
    prefs = {(r["category"], r["channel"]): r["enabled"] for r in db.rows("SELECT * FROM notification_prefs")}
    quiet = _in_quiet_now()
    out = []
    for ch in channels:
        if category is not None and prefs.get((category, ch)) == 0:
            continue  # user turned this category off on this channel
        if quiet and priority in ("low", "normal") and ch in _INTRUSIVE:
            continue  # defer intrusive channels during quiet hours — still shown in-app
        out.append(ch)
    return out or ["in_app"]


def add(kind: str, title: str, body: str, route: str, *, priority: str = "normal", category: str | None = None,
        role: str = "user", channels: list[str] | None = None, data: dict | None = None,
        dedup_key: str | None = None, ts: str | None = None) -> int:
    """Insert a notification (idempotent on dedup_key) and enqueue its out-of-app channel sends.

    Returns the row id (existing row's id when the dedup_key was already present — no duplicate outbox rows)."""
    dedup_key = dedup_key or f"{kind}:{title}"
    ts = ts or _now()
    chans = channels if channels is not None else CHANNELS.get(priority, ["in_app"])
    existing = db.one("SELECT id FROM notifications WHERE dedup_key = ?", (dedup_key,))
    if existing:
        return existing["id"]
    chans = _effective_channels(category, priority, chans)
    nid = db.exec_(
        """INSERT INTO notifications (ts, role, kind, category, priority, title, body, route, data, dedup_key, channels)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (ts, role, kind, category, priority, title, body, route, db.j(data or {}), dedup_key, db.j(chans)))
    for ch in chans:
        if ch in _OUTBOX_CHANNELS:
            db.exec_("INSERT INTO notif_outbox (notif_id, channel) VALUES (?,?)", (nid, ch))
    return nid


def listing(include_read: bool = True, limit: int = 100) -> list[dict]:
    """Stored notifications newest first, shaped like the computed list in features.notifications()."""
    sql = "SELECT * FROM notifications"
    if not include_read:
        sql += " WHERE read_at IS NULL"
    sql += " ORDER BY ts DESC LIMIT ?"
    out = []
    for r in db.rows(sql, (limit,)):
        out.append({"kind": r["kind"], "title": r["title"], "body": r["body"], "route": r["route"],
                    "ts": r["ts"], "priority": r["priority"], "category": r["category"],
                    "key": r["dedup_key"], "read": r["read_at"] is not None,
                    "ack": r["ack_at"] is not None, "id": r["id"]})
    return out


def mark_read(keys: list[str]) -> int:
    n = 0
    for k in keys:
        n += db.exec_("UPDATE notifications SET read_at = ? WHERE dedup_key = ? AND read_at IS NULL", (_now(), k))
    return n


def ack(notif_id: int, by: str = "") -> None:
    db.exec_("UPDATE notifications SET ack_at = ? WHERE id = ? AND ack_at IS NULL", (_now(), notif_id))
    if by:
        db.exec_("UPDATE notifications SET data = json_set(COALESCE(data,'{}'), '$.acked_by', ?) WHERE id = ?", (by, notif_id))


def pending_critical_unacked(older_than_min: int = 30) -> list[dict]:
    """Critical notifications not yet acknowledged — the Phase-1 escalation cron's input (doctor → centre)."""
    rows = db.rows("SELECT * FROM notifications WHERE priority = 'critical' AND ack_at IS NULL ORDER BY ts")
    cutoff = datetime.now().timestamp() - older_than_min * 60
    out = []
    for r in rows:
        try:
            if datetime.fromisoformat(r["ts"]).timestamp() <= cutoff:
                out.append(r)
        except ValueError:
            out.append(r)
    return out


# --- outbox (drained by the Phase-1 delivery cron) ---------------------------------------------------------------

_MAX_ATTEMPTS = 5


def outbox_pending(limit: int = 50) -> list[dict]:
    return db.rows("SELECT * FROM notif_outbox WHERE status = 'pending' ORDER BY id LIMIT ?", (limit,))


def outbox_mark(outbox_id: int, status: str, error: str | None = None) -> None:
    db.exec_("UPDATE notif_outbox SET status = ?, attempts = attempts + 1, last_error = ?, sent_at = ? WHERE id = ?",
             (status, error, _now() if status == "sent" else None, outbox_id))


def drain_outbox(limit: int = 50) -> dict:
    """Deliver pending out-of-app sends via the credential-gated adapters. Called by the Phase-1 cron.

    sent → done; skipped (no provider creds / no recipient) → terminal, a fresh notification re-enqueues later;
    transient error → stays pending and retries, giving up as 'failed' after _MAX_ATTEMPTS."""
    from . import senders
    sent = skipped = errored = 0
    for ob in outbox_pending(limit):
        n = db.one("SELECT * FROM notifications WHERE id = ?", (ob["notif_id"],))
        if not n:
            outbox_mark(ob["id"], "failed", "notification missing")
            continue
        status, err = senders.send(ob["channel"], n)
        if status == "sent":
            outbox_mark(ob["id"], "sent"); sent += 1
        elif status == "skipped":
            outbox_mark(ob["id"], "skipped", err); skipped += 1
        else:
            errored += 1
            if ob["attempts"] + 1 >= _MAX_ATTEMPTS:
                outbox_mark(ob["id"], "failed", err)
            else:  # keep pending for the next drain
                db.exec_("UPDATE notif_outbox SET attempts = attempts + 1, last_error = ? WHERE id = ?", (err, ob["id"]))
    return {"sent": sent, "skipped": skipped, "errored": errored}


def escalate(older_than_min: int = 30) -> dict:
    """Patient-side escalation sweep for the critical closed loop: re-ping unacknowledged critical alerts (re-enqueue
    their intrusive channels) and nudge the clinician hook. The cross-tenant doctor→centre fan-out itself lives in
    notify_clinicians_of_critical (a Phase-1 tenancy-aware item). Run from the cron alongside drain_outbox()."""
    bumped = 0
    for n in pending_critical_unacked(older_than_min):
        for ch in ("push", "sms", "whatsapp"):
            db.exec_("INSERT INTO notif_outbox (notif_id, channel) VALUES (?,?)", (n["id"], ch))
        notify_clinicians_of_critical(db.unj(n.get("data"), {}).get("report_id"), db.unj(n.get("data"), {}).get("clinician_detail", []))
        bumped += 1
    return {"escalated": bumped}


# --- the ingest safety step --------------------------------------------------------------------------------------

def notify_clinicians_of_critical(report_id: int, detail: list[dict]) -> None:
    """Hook for the doctor-D1 / centre-C1 critical path. Cross-tenant fan-out through the care graph is a
    Phase-1 item (needs tenancy linkage); for now the clinical detail is persisted on the patient notification's
    `data` so the delivery path has it. Intentionally a documented no-op here."""
    return None


def auto_flag_report(report_id: int) -> dict:
    """Run the critical-value auto-flag over a freshly-saved report and emit the right member notification.

    Precedence: any critical → U4 (route-to-clinician, no numbers); else any out-of-range → U3; else U1.
    Provenance (marker, value, threshold) is recorded on the notification's `data` for audit (DPDP) and for the
    clinician delivery path. Does NOT mutate results.status (keeps engine/derived behaviour unchanged)."""
    rep = db.one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not rep:
        return {"critical": [], "out_of_range": [], "notif": None}
    panel = rep.get("title") or rep.get("panel") or "lab"
    crit: list[dict] = []
    oor: list[dict] = []
    for r in db.rows("SELECT marker_id, value_num, unit, ref_low, ref_high FROM results WHERE report_id = ?", (report_id,)):
        cls = criticals.classify(r["marker_id"], r["value_num"], r["ref_low"], r["ref_high"])
        if cls is None:
            continue
        name = MARKERS.get(r["marker_id"], (r["marker_id"],))[0]
        item = {"marker_id": r["marker_id"], "name": name, "value": r["value_num"], "unit": r["unit"]}
        if cls == "critical":
            item["threshold"] = criticals.CRITICAL.get(r["marker_id"])
            crit.append(item)
        elif cls == "out_of_range":
            oor.append(item)

    route = f"/report/{report_id}"
    if crit:
        nid = add(
            "critical",
            "An important result needs your attention",
            f"A result in your recent {panel} report needs review. Please open Telomy and talk to your clinician.",
            route, priority="critical", category="result",
            data={"report_id": report_id, "clinician_detail": crit, "rule": "panic-value", "out_of_range": oor},
            dedup_key=f"critical:{report_id}")
        notify_clinicians_of_critical(report_id, crit)
        return {"critical": crit, "out_of_range": oor, "notif": nid}
    if oor:
        nid = add(
            "abnormal",
            "A result is outside your range",
            f"{len(oor)} marker(s) in your {panel} report are outside range — review them with Sinc or your clinician.",
            route, priority="high", category="result",
            data={"report_id": report_id, "out_of_range": oor}, dedup_key=f"abnormal:{report_id}")
        return {"critical": [], "out_of_range": oor, "notif": nid}
    nid = add(
        "result", "Lab result ready", f"Your {panel} report is ready to view.",
        route, priority="normal", category="result",
        data={"report_id": report_id}, dedup_key=f"result:{report_id}")
    return {"critical": [], "out_of_range": [], "notif": nid}
