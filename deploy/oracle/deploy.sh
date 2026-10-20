#!/usr/bin/env bash
# Deploy the Telomy backend code to the Oracle Cloud production VM.
# RUN THIS FROM YOUR MAC (the operator machine), from the repo root:
#     bash deploy/oracle/deploy.sh            # deploy for real
#     bash deploy/oracle/deploy.sh --dry-run  # show what rsync would do, change nothing
#
# What it does, conservatively:
#   1. Backs up the REMOTE DB first (sqlite3 .backup -> /opt/telomy/backups/, timestamped).
#   2. rsyncs backend/app + requirements files to /opt/telomy.
#   3. Installs any new Python deps into the remote .venv.
#   4. sudo systemctl restart telomy.
#   5. curls the public /health endpoint to confirm it came back up.
#
# It NEVER touches /opt/telomy/telomy.db or /etc/telomy.env (rsync excludes them
# and never uses --delete at the repo root). It never drops tables or runs
# migrations — schema changes are out of scope for this script and must be done
# deliberately by hand.
set -euo pipefail

# --- config ---------------------------------------------------------------
HOST_IP="129.225.98.159"
SSH_USER="opc"
SSH_KEY="$HOME/.ssh/telomy-oracle.key"
APP="/opt/telomy"
HEALTH_URL="https://129-225-98-159.sslip.io/health"

# Repo root = two levels up from this script, resolved absolutely.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
elif [ -n "${1:-}" ]; then
  echo "unknown argument: $1 (only --dry-run is supported)" >&2
  exit 2
fi

SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new ${SSH_USER}@${HOST_IP}"
TARGET="${SSH_USER}@${HOST_IP}"

# --- preflight ------------------------------------------------------------
echo "== preflight"
[ -r "$SSH_KEY" ]            || { echo "error: SSH key not readable: $SSH_KEY" >&2; exit 1; }
[ -d "$REPO_ROOT/backend/app" ] || { echo "error: backend/app not found under $REPO_ROOT" >&2; exit 1; }
[ -f "$REPO_ROOT/backend/requirements.txt" ] || { echo "error: backend/requirements.txt missing" >&2; exit 1; }
command -v rsync >/dev/null || { echo "error: rsync not found on this machine" >&2; exit 1; }
echo "   repo:   $REPO_ROOT"
echo "   target: ${TARGET}:${APP}"
[ "$DRY_RUN" = 1 ] && echo "   mode:   DRY RUN (no changes will be made)"

# rsync excludes: never ship caches, and never let these leave or land on the DB/env.
RSYNC_EXCLUDES=(
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.pytest_cache/'
  --exclude '*.db'
  --exclude '*.db-wal'
  --exclude '*.db-shm'
  --exclude '.env'
  --exclude '.env.*'
)

# --- dry run short-circuit -------------------------------------------------
if [ "$DRY_RUN" = 1 ]; then
  echo "== rsync (dry run): backend/app -> ${APP}/app"
  rsync -azvn --itemize-changes "${RSYNC_EXCLUDES[@]}" \
    -e "ssh -i $SSH_KEY" \
    "$REPO_ROOT/backend/app/" "${TARGET}:${APP}/app/"
  echo "== rsync (dry run): requirements -> ${APP}/"
  rsync -azvn --itemize-changes \
    -e "ssh -i $SSH_KEY" \
    "$REPO_ROOT/backend/requirements.txt" "${TARGET}:${APP}/requirements.txt"
  echo "== dry run complete — nothing was changed on the server"
  exit 0
fi

# --- 1. remote DB backup (first, before any change) -----------------------
echo "== backing up remote DB first"
$SSH 'set -euo pipefail
  mkdir -p /opt/telomy/backups
  TS=$(date +%Y%m%d-%H%M%S)
  if [ -f /opt/telomy/telomy.db ]; then
    sqlite3 /opt/telomy/telomy.db ".backup /opt/telomy/backups/telomy-predeploy-$TS.db"
    echo "   backup: /opt/telomy/backups/telomy-predeploy-$TS.db"
    find /opt/telomy/backups -name "telomy-predeploy-*.db" -mtime +14 -delete
  else
    echo "   warning: /opt/telomy/telomy.db not found, skipping DB backup"
  fi'

# --- 2. sync code ----------------------------------------------------------
# NOTE: --delete only applies under app/ so stale modules are removed, but it can
# never reach the DB or env (those live at $APP root, not under app/).
echo "== syncing backend/app -> ${APP}/app"
rsync -az --delete --itemize-changes "${RSYNC_EXCLUDES[@]}" \
  -e "ssh -i $SSH_KEY" \
  "$REPO_ROOT/backend/app/" "${TARGET}:${APP}/app/"

echo "== syncing requirements.txt -> ${APP}/"
rsync -az --itemize-changes \
  -e "ssh -i $SSH_KEY" \
  "$REPO_ROOT/backend/requirements.txt" "${TARGET}:${APP}/requirements.txt"

# Ship the optional voice requirements file too if present (install is manual).
if [ -f "$REPO_ROOT/backend/requirements-voice.txt" ]; then
  rsync -az --itemize-changes -e "ssh -i $SSH_KEY" \
    "$REPO_ROOT/backend/requirements-voice.txt" "${TARGET}:${APP}/requirements-voice.txt"
fi

# --- 3. install deps into the remote venv ---------------------------------
echo "== installing Python deps into remote .venv"
$SSH 'set -euo pipefail
  cd /opt/telomy
  if [ -x .venv/bin/pip ]; then
    .venv/bin/pip install -q -r requirements.txt
  elif command -v uv >/dev/null; then
    uv pip install -q --python .venv/bin/python -r requirements.txt
  else
    echo "error: no pip or uv in remote .venv" >&2; exit 1
  fi
  echo "   deps up to date"'

# --- 4. restart the service ------------------------------------------------
echo "== restarting telomy service"
$SSH 'sudo systemctl restart telomy'

# --- 5. health check -------------------------------------------------------
echo "== waiting for service to come up"
sleep 4
echo "== health check: $HEALTH_URL"
if curl -fsS --max-time 15 "$HEALTH_URL" >/dev/null; then
  curl -fsS --max-time 15 "$HEALTH_URL"; echo
  echo "== deploy OK"
else
  echo "error: health check FAILED — service may be down." >&2
  echo "       inspect:  $SSH 'sudo journalctl -u telomy -n 100 --no-pager'" >&2
  echo "       rollback: see deploy/README.md" >&2
  exit 1
fi
