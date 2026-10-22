"""Switch a Telomy server from the seeded TEST profile to the real user's own profile — without losing real data.

Creates a NEW database (the old one is untouched and stays as the backup): all schemas initialised, a real (non-test)
profile shell, and every table that only real devices / the real user write copied across wholesale. Seeded demo
content (Test User profile, 120 days of generated signals, demo labs, demo events, demo centre sessions) stays behind.
usage: TELOMY_DB=<new.db> python -m tools.make_real_db <old.db>
Then point TELOMY_DB at <new.db> and restart. Reverting = pointing TELOMY_DB back at <old.db>.
"""
import os
import sqlite3
import sys

REAL_TABLES = [
    "band_minutes", "band_events", "band_recordings", "band_captures", "ecg_strips",            # Telomy patch uploads
    "whoop_rows", "whoop_batches", "whoop_staging", "whoop_state", "whoop_superseded",          # WHOOP via NOOP push
    "voice_samples", "chats", "messages", "routines", "routine_log",                           # the user's own Sinc use
    "devices", "device_keys", "telemetry",                                                     # centre device inventory
    "exposure",                                                                                # public environment cache
]


def main(old: str):
    new = os.environ["TELOMY_DB"]
    if os.path.abspath(new) == os.path.abspath(old):
        sys.exit("TELOMY_DB must point at a NEW file")
    if os.path.exists(new):
        sys.exit(f"{new} already exists — refusing to overwrite")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import db
    db.DB_PATH = new
    db.init(reset=False)
    from app import activities, band, devices, exposome, plans, rx, roles, routine, summaries, therapy, voice, whoop
    for m in (roles, plans, therapy, rx, summaries, voice, routine, activities, exposome, devices, band, whoop):
        m.init()
    db.exec_("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)", (db.j({
        "name": "", "first_name": "", "onboarded": True, "is_test_profile": False, "city": "Bengaluru",
        "goal": "Track my health with my own devices"}),))
    src = sqlite3.connect(old)
    dst = sqlite3.connect(new)
    copied = {}
    for t in REAL_TABLES:
        try:
            cols = [r[1] for r in src.execute(f"PRAGMA table_info({t})")]
            dcols = {r[1] for r in dst.execute(f"PRAGMA table_info({t})")}
        except sqlite3.Error:
            continue
        cols = [c for c in cols if c in dcols]
        if not cols:
            continue
        rows = src.execute(f"SELECT {','.join(cols)} FROM {t}").fetchall()
        dst.execute(f"DELETE FROM {t}")
        dst.executemany(f"INSERT OR REPLACE INTO {t} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)
        copied[t] = len(rows)
    # the user's own logged events after the seed date (none expected, but never drop them)
    seed_end = src.execute("SELECT MAX(day) FROM signals").fetchone()[0] or "1970-01-01"
    ev = src.execute("SELECT ts, kind, label, severity, data, source FROM events WHERE ts > ?", (seed_end + "T23:59",)).fetchall()
    dst.executemany("INSERT INTO events (ts, kind, label, severity, data, source) VALUES (?,?,?,?,?,?)", ev)
    copied["events (after seed)"] = len(ev)
    dst.commit()
    print("new real database:", new)
    for k, v in copied.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1])
