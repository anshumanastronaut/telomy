# Telomy ops / deploy

Two environments, two very different jobs.

| | Mac (dev / study) | Oracle Cloud (production) |
|---|---|---|
| Runs | `uvicorn app.main:app` on `:8787` | same, behind Caddy HTTPS |
| DB | `backend/telomy-live.db` (SQLite WAL) | `/opt/telomy/telomy.db` |
| Supervision | launchd (`com.telomy.backend`) | systemd (`telomy`) |
| Backups | launchd nightly, `backend/backups/` | cron nightly, `/opt/telomy/backups/` |
| Secrets | `backend/.whoop-token`, `backend/.env` | `/etc/telomy.env` |

## Mac: keepalive + nightly backup

Fixes the gap where the backend ran under a bare `nohup` with no supervision and
no backups.

**Keepalive** — `deploy/mac/com.telomy.backend.plist` is a launchd LaunchAgent
with `KeepAlive` + `RunAtLoad`, so the backend restarts on crash and on reboot.
It runs `backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port
8787` with `TELOMY_DB` pointed at `telomy-live.db`. The WHOOP token is read at
launch from `backend/.whoop-token` (git-ignored; `chmod 600`). If that file is
absent the backend still starts and WHOOP ingest is simply disabled.

**Backup** — `deploy/mac/backup-db.sh` does a WAL-safe `sqlite3 .backup` into
`backend/backups/`, timestamped, verifies `PRAGMA integrity_check`, and keeps the
last 14. `deploy/mac/com.telomy.backup.plist` runs it nightly at ~03:30.

Install (one time):

```sh
mkdir -p backend/logs backend/backups
chmod +x deploy/mac/backup-db.sh

cp deploy/mac/com.telomy.backend.plist ~/Library/LaunchAgents/
cp deploy/mac/com.telomy.backup.plist  ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.telomy.backend.plist
launchctl load -w ~/Library/LaunchAgents/com.telomy.backup.plist

# verify
launchctl list | grep com.telomy
launchctl start com.telomy.backup        # run a backup now
ls -lh backend/backups/
```

Stop managing either (back to manual):

```sh
launchctl unload -w ~/Library/LaunchAgents/com.telomy.backend.plist
launchctl unload -w ~/Library/LaunchAgents/com.telomy.backup.plist
```

Logs: `backend/logs/backend.{out,err}.log` and `backend/logs/backup.{out,err}.log`.

> If you load the keepalive agent, first stop the old `nohup` uvicorn so two
> processes don't fight over `:8787` (`pkill -f 'uvicorn app.main:app'`).

## Cloud: deploy procedure

One-time server provisioning is `deploy/oracle/setup.sh` (swap, firewall,
Python via uv, the `telomy` systemd service, Caddy HTTPS, nightly cron backup).
Routine code pushes use `deploy/oracle/deploy.sh`, **run from your Mac** at the
repo root:

```sh
bash deploy/oracle/deploy.sh --dry-run   # preview the rsync, change nothing
bash deploy/oracle/deploy.sh             # deploy for real
```

The deploy script, in order: backs up the remote DB first
(`sqlite3 .backup` → `/opt/telomy/backups/telomy-predeploy-<ts>.db`), rsyncs
`backend/app` + `requirements.txt` to `/opt/telomy`, installs any new deps into
the remote `.venv`, `sudo systemctl restart telomy`, then curls
`https://129-225-98-159.sslip.io/health`.

**Safety guarantees**

- The production DB `/opt/telomy/telomy.db` and `/etc/telomy.env` are **never
  overwritten** — both are rsync-excluded, and `--delete` is scoped to `app/`
  only (it can't reach the DB or env at the `/opt/telomy` root).
- No schema changes: the script never drops tables and runs no migrations.
  Apply those deliberately by hand when needed.
- A failed health check exits non-zero and prints the journalctl + rollback
  hints instead of leaving you guessing.

## Rollback (cloud)

1. **Code** — re-deploy a known-good checkout:
   ```sh
   git checkout <last-good-sha>
   bash deploy/oracle/deploy.sh
   ```
   or restart whatever is currently on disk:
   ```sh
   ssh -i ~/.ssh/telomy-oracle.key opc@129.225.98.159 'sudo systemctl restart telomy'
   ```
2. **Database** — restore the timestamped pre-deploy backup:
   ```sh
   ssh -i ~/.ssh/telomy-oracle.key opc@129.225.98.159
   sudo systemctl stop telomy
   ls -lt /opt/telomy/backups/                       # pick the backup to restore
   cp /opt/telomy/telomy.db /opt/telomy/telomy.db.bad # keep the current one aside
   cp /opt/telomy/backups/telomy-predeploy-<ts>.db /opt/telomy/telomy.db
   sudo systemctl start telomy
   curl -fsS https://129-225-98-159.sslip.io/health
   ```
3. **Logs** — `sudo journalctl -u telomy -n 200 --no-pager`.

## Rollback (Mac)

The live DB backups are in `backend/backups/telomy-live-<ts>.db`. To restore:

```sh
launchctl stop com.telomy.backend
cp backend/telomy-live.db backend/telomy-live.db.bad
cp backend/backups/telomy-live-<ts>.db backend/telomy-live.db
launchctl start com.telomy.backend
```
