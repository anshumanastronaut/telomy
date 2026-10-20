#!/usr/bin/env bash
# Consistent, WAL-safe SQLite backup of the Mac dev/study database.
# Uses `sqlite3 .backup`, which is safe to run while the backend is live
# (it reads a consistent snapshot even with WAL). Timestamped output into
# backend/backups/, keeping the most recent 14 and deleting older ones.
#
# Run manually:   bash deploy/mac/backup-db.sh
# Scheduled:      via deploy/mac/com.telomy.backup.plist (nightly ~03:30)
set -euo pipefail

ROOT="/Users/anshuman/telomy-app"
DB="$ROOT/backend/telomy-live.db"
DEST_DIR="$ROOT/backend/backups"
KEEP=14

# Prefer the project's expected DB path, but honour an override.
DB="${TELOMY_DB:-$DB}"

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "error: sqlite3 not found on PATH" >&2
  exit 1
fi

if [ ! -f "$DB" ]; then
  echo "error: database not found: $DB" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"

TS="$(date +%Y%m%d-%H%M%S)"
DEST="$DEST_DIR/telomy-live-$TS.db"
TMP="$DEST.partial"

# Clean up any partial file if we die mid-backup.
trap 'rm -f "$TMP"' EXIT

echo "[backup] $DB -> $DEST"
# .backup is atomic from the reader's view and WAL-safe.
sqlite3 "$DB" ".backup '$TMP'"

# Sanity check the copy before publishing it.
if ! sqlite3 "$TMP" "PRAGMA integrity_check;" | grep -q '^ok$'; then
  echo "error: integrity check failed on backup, discarding" >&2
  exit 1
fi

mv "$TMP" "$DEST"
trap - EXIT
echo "[backup] ok ($(du -h "$DEST" | cut -f1))"

# Retention: keep the newest $KEEP, delete the rest. Sort by name (names are
# timestamped, so lexical == chronological), then drop all but the last $KEEP.
# Written for bash 3.2 (macOS default): no `mapfile`, no `head -n -N` (GNU-only).
echo "[backup] pruning, keeping last $KEEP"
total=$(ls -1 "$DEST_DIR"/telomy-live-*.db 2>/dev/null | wc -l | tr -d ' ')
if [ "$total" -gt "$KEEP" ]; then
  drop=$(( total - KEEP ))
  ls -1 "$DEST_DIR"/telomy-live-*.db 2>/dev/null | sort | head -n "$drop" \
    | while IFS= read -r old; do
        echo "[backup] rm $old"
        rm -f "$old"
      done
fi

echo "[backup] done"
