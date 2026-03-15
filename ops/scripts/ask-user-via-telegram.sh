#!/usr/bin/env bash
# ask-user-via-telegram.sh — singleton poller: races stdin vs Telegram reply.
# Usage: answer=$(ops/scripts/ask-user-via-telegram.sh "Your question?")
# Returns the user's answer on stdout.
# Requires: flock (brew install util-linux on macOS), sops, curl, python3
# MAX_TIMEOUT env var overrides the 2-hour default (useful for tests).
set -euo pipefail

QUESTION="${1:?Usage: ask-user-via-telegram.sh \"question\"}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${OPS_DIR}/.." && pwd)"

TTY_PATH=$(tty 2>/dev/null) || TTY_PATH="notty"
TTY_ID=$(printf '%s' "$TTY_PATH" | tr '/' '_')
LOCKFILE="/tmp/dechord-telegram-ask-${TTY_ID}.lock"
OFFSET_FILE="/tmp/dechord-telegram-offset-${TTY_ID}.txt"

POLL_INTERVAL=30
MAX_TIMEOUT="${MAX_TIMEOUT:-7200}"  # 2 hours; override via env for tests

# ── Prerequisite checks ──────────────────────────────────────────────────────

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ Missing required command: ${cmd}" >&2
    if [[ "$cmd" == "flock" ]]; then
      echo "   Install with: brew install util-linux" >&2
    fi
    exit 1
  fi
}

require_command flock
require_command sops
require_command curl
require_command python3

# ── Singleton lock ────────────────────────────────────────────────────────────

exec 9>"$LOCKFILE"
flock_exit=0
flock -n 9 || flock_exit=$?
if [[ $flock_exit -ne 0 ]]; then
  if [[ $flock_exit -eq 1 ]]; then
    echo "⚠️  Telegram poller already active — answer at terminal:" >&2
    read -r _fallback_answer
    printf '%s\n' "$_fallback_answer"
    exit 0
  else
    echo "❌ flock failed (exit ${flock_exit}) — is flock installed? brew install util-linux" >&2
    exit 1
  fi
fi

# ── Startup cleanup ───────────────────────────────────────────────────────────

# Always delete stale offset file — never trust one left by a killed process.
rm -f "$OFFSET_FILE"

cleanup() {
  rm -f "$OFFSET_FILE"
}
trap cleanup EXIT

# ── Secret decryption (same pattern as send-telegram-summary.sh) ──────────────

parse_yaml_value() {
  local key="$1"
  local content="$2"
  python3 - "$key" "$content" <<'PY'
import re, sys
key = sys.argv[1]
text = sys.argv[2]
pattern = rf'^\s*{re.escape(key)}:\s*["\']?([^"\n\']+)["\']?\s*$'
match = re.search(pattern, text, re.MULTILINE)
if not match:
    raise SystemExit(f"Missing key: {key}")
print(match.group(1))
PY
}

if [[ -z "${SOPS_AGE_KEY_FILE:-}" && -f "${HOME}/.config/sops/age/keys.txt" ]]; then
  export SOPS_AGE_KEY_FILE="${HOME}/.config/sops/age/keys.txt"
fi

SECRETS_FILE="${TELEGRAM_SECRETS_FILE:-${OPS_DIR}/secrets/telegram.sops.yaml}"
if [[ ! -f "$SECRETS_FILE" ]]; then
  echo "❌ Secrets file not found: ${SECRETS_FILE}" >&2
  exit 1
fi

DECRYPTED="$(sops -d "$SECRETS_FILE")"
BOT_TOKEN="$(parse_yaml_value "bot_token" "$DECRYPTED")"
CHAT_ID="$(parse_yaml_value "chat_id" "$DECRYPTED")"

# ── Telegram helpers ──────────────────────────────────────────────────────────

tg_send() {
  local text="$1"
  curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${text}" \
    >/dev/null 2>&1 || true
}

tg_get_updates() {
  local offset="$1"
  curl -fsS \
    "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=$((offset + 1))&timeout=25&allowed_updates=message" \
    2>/dev/null || echo '{}'
}

tg_max_update_id() {
  local response
  response=$(curl -fsS \
    "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?limit=100&timeout=0" \
    2>/dev/null || echo '{}')
  python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
results = data.get('result', [])
print(results[-1]['update_id'] if results else 0)
" <<< "$response"
}

# ── Main flow ─────────────────────────────────────────────────────────────────

REPO_NAME="$(basename "$REPO_ROOT")"
BRANCH_NAME="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"

# Fetch baseline update_id (ignore messages that arrived before we started).
CURRENT_OFFSET=$(tg_max_update_id)
if [[ "$CURRENT_OFFSET" == "0" ]]; then
  echo "⚠️  Could not fetch baseline update_id (curl failed?) — pre-existing messages may be accepted as answers" >&2
fi
printf '%s\n' "$CURRENT_OFFSET" > "$OFFSET_FILE"
chmod 600 "$OFFSET_FILE"

# Send the question.
tg_send "❓ ${QUESTION}

Repo: ${REPO_NAME}  Branch: ${BRANCH_NAME}"

START_TIME=$(date +%s)

# ── Poll loop ─────────────────────────────────────────────────────────────────

while true; do
  NOW=$(date +%s)
  ELAPSED=$(( NOW - START_TIME ))

  if [[ $ELAPSED -ge $MAX_TIMEOUT ]]; then
    echo "⚠️  Telegram timeout reached (2h) — waiting at terminal" >&2
    read -r _timeout_answer
    printf '%s\n' "$_timeout_answer"
    exit 0
  fi

  # Check stdin first (1-second window).
  if read -t 1 -r stdin_answer 2>/dev/null; then
    tg_send "✅ Got it! Forwarding to agent — continuing work..."
    printf '%s\n' "$stdin_answer"
    exit 0
  fi

  # Poll Telegram (long-poll, up to 25s). Parse reply inline — no helper function.
  TG_RESPONSE=$(tg_get_updates "$CURRENT_OFFSET")
  REPLY=$(printf '%s' "$TG_RESPONSE" | python3 - "$CHAT_ID" <<'PY'
import json, sys
chat_id = sys.argv[1]
data = json.loads(sys.stdin.read())
for update in data.get("result", []):
    msg = update.get("message", {})
    if str(msg.get("chat", {}).get("id", "")) == chat_id:
        text = msg.get("text", "").strip()
        print(update["update_id"])
        print(text if text else "__SKIP__")
        break
PY
2>/dev/null || true)

  if [[ -n "$REPLY" ]]; then
    NEW_OFFSET=$(printf '%s' "$REPLY" | head -1)
    REPLY_TEXT=$(printf '%s' "$REPLY" | tail -n +2)
    CURRENT_OFFSET="$NEW_OFFSET"
    printf '%s\n' "$CURRENT_OFFSET" > "$OFFSET_FILE"

    if [[ -n "$REPLY_TEXT" ]] && [[ "$REPLY_TEXT" != "__SKIP__" ]]; then
      tg_send "✅ Got it! Forwarding to agent — continuing work..."
      printf '%s\n' "$REPLY_TEXT"
      exit 0
    fi
  fi

  # Brief pause to reach ~30s total loop time (1s read + 25s curl + 4s sleep).
  sleep 4
done
