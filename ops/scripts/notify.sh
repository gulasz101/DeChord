#!/usr/bin/env bash
# notify.sh — queue a Telegram notification via TTY-scoped sentinel file.
# Usage: notify.sh "title" "summary body"
# The Stop hook in .claude/settings.json delivers it at session end.
set -euo pipefail

TITLE="${1:?Usage: notify.sh \"title\" \"summary body\"}"
SUMMARY="${2:?Usage: notify.sh \"title\" \"summary body\"}"

# Sweep stale sentinel files older than 24 hours using python3 (macOS-safe).
python3 - <<'PY' || true
import os, glob, time
threshold = time.time() - 86400
for f in glob.glob('/tmp/dechord-notify-*.pending'):
    try:
        if os.path.getmtime(f) < threshold:
            os.remove(f)
    except OSError:
        pass
PY

# Resolve TTY-scoped sentinel path. Fall back to a unique headless sentinel if no TTY.
TTY_PATH=$(tty 2>/dev/null) || TTY_PATH=""
if [ -n "$TTY_PATH" ]; then
  TTY_ID=$(printf '%s' "$TTY_PATH" | tr '/' '_')
  SENTINEL="/tmp/dechord-notify-${TTY_ID}.pending"
else
  SENTINEL="/tmp/dechord-notify-headless-$(date +%s)-$$.pending"
fi

# Write sentinel atomically: write to tmp, chmod, then rename.
TMP=$(mktemp)
trap 'rm -f "${TMP}"' EXIT

python3 - "$TITLE" "$SUMMARY" > "$TMP" <<'PY'
import json, sys
print(json.dumps({"title": sys.argv[1], "summary": sys.argv[2]}))
PY

chmod 600 "$TMP"
mv "$TMP" "$SENTINEL"

echo "✅ Notification queued: ${SENTINEL}"
