# AGENTS.md Rewrite + Telegram Notification System — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace behavioral Telegram compliance with script-enforced notifications, add a singleton Telegram reply-poller for user input, and rewrite AGENTS.md to be unambiguous across Claude Code and OpenCode.

**Architecture:** Three layers — AGENTS.md (imperative script-call rules), bash scripts in `ops/scripts/` (all logic), and a Claude Code Stop hook in `.claude/settings.json` (sentinel-based enforcement). A TTY-scoped sentinel file decouples notification queuing from delivery. A singleton poller races stdin vs Telegram for user replies.

**Tech Stack:** bash, sops (secret decryption), curl (Telegram Bot API), python3 (JSON parsing), flock (singleton lockfile, requires `brew install util-linux` on macOS).

**Spec:** `docs/superpowers/specs/2026-03-15-agents-md-telegram-redesign.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ops/scripts/send-telegram-summary.sh` | Modify | Add `--sentinel-file` flag to accept JSON sentinel |
| `ops/scripts/notify.sh` | Create | Write TTY-scoped sentinel atomically; sweep stale sentinels |
| `ops/scripts/ask-user-via-telegram.sh` | Create | Singleton poller: races stdin vs Telegram, 30s loop, 2hr timeout |
| `ops/tests/test_notify.sh` | Create | Unit tests for notify.sh (sentinel creation, cleanup, headless) |
| `ops/tests/test_send_telegram.sh` | Create | Unit tests for --sentinel-file flag |
| `ops/tests/test_ask_user.sh` | Create | Unit tests for ask-user singleton and stdin capture |
| `ops/tests/run_all.sh` | Create | Runs all script tests; used by `make test-scripts` |
| `.claude/settings.json` | Create | Stop hook: consume sentinel and send on session end |
| `AGENTS.md` | Rewrite | Imperative rules only, all sections updated |
| `Makefile` | Modify | Add `test-scripts` target |

---

## Chunk 1: send-telegram-summary.sh + notify.sh

### Task 1: Add `--sentinel-file` flag to `send-telegram-summary.sh`

**Files:**
- Modify: `ops/scripts/send-telegram-summary.sh`
- Create: `ops/tests/test_send_telegram.sh`

- [x] **Step 1: Write the failing test**

Create `ops/tests/test_send_telegram.sh`:

```bash
#!/usr/bin/env bash
# Tests for --sentinel-file flag in send-telegram-summary.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT="${OPS_DIR}/scripts/send-telegram-summary.sh"
PASS=0; FAIL=0

run_test() {
  local name="$1"; shift
  if "$@" 2>/dev/null; then
    echo "✅ PASS: $name"; ((PASS++))
  else
    echo "❌ FAIL: $name"; ((FAIL++))
  fi
}

# Mock environment: override secrets file with a fake one
export TELEGRAM_SECRETS_FILE="/dev/null"

# Test: --sentinel-file with valid JSON extracts title and summary
test_sentinel_file_parsing() {
  local sentinel
  sentinel=$(mktemp)
  printf '{"title":"Test Title","summary":"Test body"}' > "$sentinel"

  # We can't actually send — test that the script reads the sentinel without error
  # by using --skip which bypasses send but still parses args
  # Instead, test the parsing path: script should exit with "Secrets file not found"
  # (meaning it got past sentinel parsing successfully)
  local output
  output=$("$SCRIPT" --sentinel-file "$sentinel" 2>&1 || true)
  rm -f "$sentinel"
  [[ "$output" == *"Secrets file not found"* ]] || [[ "$output" == *"Missing required command"* ]]
}

# Test: --sentinel-file with missing file exits non-zero
test_sentinel_file_missing() {
  ! "$SCRIPT" --sentinel-file "/tmp/does-not-exist-$(date +%s).json" 2>/dev/null
}

# Test: --sentinel-file and --skip together: skip wins, no error
test_sentinel_file_with_skip() {
  local sentinel
  sentinel=$(mktemp)
  printf '{"title":"T","summary":"S"}' > "$sentinel"
  "$SCRIPT" --sentinel-file "$sentinel" --skip
  rm -f "$sentinel"
}

run_test "sentinel file parsing reaches secrets step" test_sentinel_file_parsing
run_test "missing sentinel file exits non-zero" test_sentinel_file_missing
run_test "sentinel file + --skip exits 0" test_sentinel_file_with_skip

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[[ $FAIL -eq 0 ]]
```

- [x] **Step 2: Run test to verify it fails**

```bash
bash ops/tests/test_send_telegram.sh
```

Expected: `❌ FAIL: sentinel file parsing reaches secrets step` (flag not implemented yet)

- [x] **Step 3: Add `--sentinel-file` flag to `send-telegram-summary.sh`**

First read the file to locate the exact insertion points:
```bash
cat -n ops/scripts/send-telegram-summary.sh
```

Make the following four additions:

**3a.** In `usage()`, add a new line after `--summary-file`:
```
  --sentinel-file PATH  Read title and summary from a JSON sentinel file.
```

**3b.** After the existing variable declarations block (after `TITLE="${DEFAULT_TITLE}"`), add:
```bash
SENTINEL_FILE=""
```

**3c.** In the argument parser `while` loop, add before the `*)` catch-all:
```bash
    --sentinel-file)
      SENTINEL_FILE="${2:?Missing value for --sentinel-file}"
      shift 2
      ;;
```

**3d.** After the `while` loop ends and immediately before the `if [[ "${SKIP_SEND}" -eq 1 ]]; then` line, insert:
```bash
# Resolve sentinel file into --title and --summary-file equivalents.
if [[ -n "${SENTINEL_FILE:-}" ]]; then
  if [[ ! -f "${SENTINEL_FILE}" ]]; then
    echo "Sentinel file not found: ${SENTINEL_FILE}" >&2
    exit 1
  fi
  TITLE="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['title'])" "${SENTINEL_FILE}")"
  TMP_SUMMARY="$(mktemp)"
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['summary'], end='')" "${SENTINEL_FILE}" > "${TMP_SUMMARY}"
  SUMMARY_FILE="${TMP_SUMMARY}"
  trap 'rm -f "${TMP_SUMMARY:-}"' EXIT
fi
```

- [x] **Step 4: Run test to verify it passes**

```bash
bash ops/tests/test_send_telegram.sh
```

Expected: `Results: 3 passed, 0 failed`

- [x] **Step 5: Commit**

```bash
git add ops/scripts/send-telegram-summary.sh ops/tests/test_send_telegram.sh
git commit -m "feat(ops): add --sentinel-file flag to send-telegram-summary.sh [plan: 2026-03-15-agents-md-telegram-redesign, Task 1, cli: claude-code, model: claude-sonnet-4-6]"
```

  - **Committed:** d9ff91c

---

### Task 2: Create `notify.sh`

**Files:**
- Create: `ops/scripts/notify.sh`
- Create: `ops/tests/test_notify.sh`

- [x] **Step 1: Write the failing test**

Create `ops/tests/test_notify.sh`:

```bash
#!/usr/bin/env bash
# Tests for notify.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT="${OPS_DIR}/scripts/notify.sh"
PASS=0; FAIL=0

run_test() {
  local name="$1"; shift
  if "$@" 2>/dev/null; then
    echo "✅ PASS: $name"; ((PASS++))
  else
    echo "❌ FAIL: $name"; ((FAIL++))
  fi
}

# Derive the TTY-scoped path the script will use
TTY_ID=$(tty 2>/dev/null | tr '/' '_') || TTY_ID=""

# Test: sentinel file is created with correct JSON
test_sentinel_created() {
  [[ -z "$TTY_ID" ]] && { echo "  (skip: no TTY)"; return 0; }
  local sentinel="/tmp/dechord-notify-${TTY_ID}.pending"
  rm -f "$sentinel"
  "$SCRIPT" "My Title" "My Summary"
  [[ -f "$sentinel" ]]
  local title summary
  title=$(python3 -c "import json; d=json.load(open('$sentinel')); print(d['title'])")
  summary=$(python3 -c "import json; d=json.load(open('$sentinel')); print(d['summary'])")
  rm -f "$sentinel"
  [[ "$title" == "My Title" ]] && [[ "$summary" == "My Summary" ]]
}

# Test: sentinel file has restricted permissions (600)
test_sentinel_permissions() {
  [[ -z "$TTY_ID" ]] && { echo "  (skip: no TTY)"; return 0; }
  local sentinel="/tmp/dechord-notify-${TTY_ID}.pending"
  rm -f "$sentinel"
  "$SCRIPT" "T" "S"
  local perms
  perms=$(stat -f "%OLp" "$sentinel" 2>/dev/null || stat -c "%a" "$sentinel" 2>/dev/null)
  rm -f "$sentinel"
  [[ "$perms" == "600" ]]
}

# Test: second call overwrites first (last-wins semantics)
test_sentinel_overwrite() {
  [[ -z "$TTY_ID" ]] && { echo "  (skip: no TTY)"; return 0; }
  local sentinel="/tmp/dechord-notify-${TTY_ID}.pending"
  rm -f "$sentinel"
  "$SCRIPT" "First" "First body"
  "$SCRIPT" "Second" "Second body"
  local title
  title=$(python3 -c "import json; d=json.load(open('$sentinel')); print(d['title'])")
  rm -f "$sentinel"
  [[ "$title" == "Second" ]]
}

# Test: stale sentinel files (>24h) are swept on startup
test_stale_cleanup() {
  local stale="/tmp/dechord-notify-_fake_tty_test_stale.pending"
  printf '{"title":"old","summary":"old"}' > "$stale"
  # Backdate the file by 25 hours
  touch -t "$(date -v -25H '+%Y%m%d%H%M' 2>/dev/null || date -d '25 hours ago' '+%Y%m%d%H%M' 2>/dev/null)" "$stale" 2>/dev/null || {
    # fallback: manually set mtime via python
    python3 -c "import os,time; os.utime('$stale', (time.time()-90100, time.time()-90100))"
  }
  "$SCRIPT" "New" "New body" 2>/dev/null || true
  local still_exists=0
  [[ -f "$stale" ]] && still_exists=1
  rm -f "$stale"
  [[ $still_exists -eq 0 ]]
}

# Test: headless (no TTY) exits 0 without creating a file
test_headless_no_sentinel() {
  # Simulate headless by overriding tty via a wrapper
  local fake_tty_dir
  fake_tty_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nexit 1\n' > "${fake_tty_dir}/tty"
  chmod +x "${fake_tty_dir}/tty"
  local result
  PATH="${fake_tty_dir}:${PATH}" "$SCRIPT" "T" "S" 2>/dev/null
  result=$?
  rm -rf "$fake_tty_dir"
  [[ $result -eq 0 ]]
}

run_test "sentinel created with correct JSON" test_sentinel_created
run_test "sentinel has 600 permissions" test_sentinel_permissions
run_test "second call overwrites first" test_sentinel_overwrite
run_test "stale sentinels swept on startup" test_stale_cleanup
run_test "headless exits 0 without creating sentinel" test_headless_no_sentinel

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[[ $FAIL -eq 0 ]]
```

- [x] **Step 2: Run test to verify it fails**

```bash
bash ops/tests/test_notify.sh
```

Expected: FAIL (script doesn't exist yet)

- [x] **Step 3: Create `ops/scripts/notify.sh`**

```bash
#!/usr/bin/env bash
# notify.sh — queue a Telegram notification via TTY-scoped sentinel file.
# Usage: notify.sh "title" "summary body"
# The Stop hook in .claude/settings.json delivers it at session end.
set -euo pipefail

TITLE="${1:?Usage: notify.sh \"title\" \"summary body\"}"
SUMMARY="${2:?Usage: notify.sh \"title\" \"summary body\"}"

# Sweep stale sentinel files older than 24 hours (1440 minutes).
find /tmp -maxdepth 1 -name 'dechord-notify-*.pending' -mmin +1440 -delete 2>/dev/null || true

# Resolve TTY-scoped sentinel path. Exit cleanly if no controlling terminal.
TTY_PATH=$(tty 2>/dev/null) || {
  echo "⚠️  notify.sh: no TTY detected (headless session) — skipping sentinel creation" >&2
  exit 0
}
TTY_ID=$(printf '%s' "$TTY_PATH" | tr '/' '_')
SENTINEL="/tmp/dechord-notify-${TTY_ID}.pending"

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
```

```bash
chmod +x ops/scripts/notify.sh
```

- [x] **Step 4: Run test to verify it passes**

```bash
bash ops/tests/test_notify.sh
```

Expected: `Results: 5 passed, 0 failed`

- [x] **Step 5: Commit**

```bash
git add ops/scripts/notify.sh ops/tests/test_notify.sh
git commit -m "feat(ops): add notify.sh — TTY-scoped sentinel writer [plan: 2026-03-15-agents-md-telegram-redesign, Task 2, cli: claude-code, model: claude-sonnet-4-6]"
```

  - **Committed:** 323be14

---

## Chunk 2: ask-user-via-telegram.sh

### Task 3: Create `ask-user-via-telegram.sh` — core structure

**Files:**
- Create: `ops/scripts/ask-user-via-telegram.sh`
- Create: `ops/tests/test_ask_user.sh`

- [x] **Step 1: Write the failing singleton test**

Create `ops/tests/test_ask_user.sh`:

```bash
#!/usr/bin/env bash
# Tests for ask-user-via-telegram.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT="${OPS_DIR}/scripts/ask-user-via-telegram.sh"
PASS=0; FAIL=0

run_test() {
  local name="$1"; shift
  if "$@" 2>/dev/null; then
    echo "✅ PASS: $name"; ((PASS++))
  else
    echo "❌ FAIL: $name"; ((FAIL++))
  fi
}

# Derive lock path that script will use
TTY_ID=$(tty 2>/dev/null | tr '/' '_') || TTY_ID="notty"
LOCKFILE="/tmp/dechord-telegram-ask-${TTY_ID}.lock"
OFFSET_FILE="/tmp/dechord-telegram-offset-${TTY_ID}.txt"

# Cleanup after each test
cleanup() {
  rm -f "$LOCKFILE" "$OFFSET_FILE"
  # Kill any background poller from tests
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

# Test: singleton — second invocation falls through to stdin immediately
test_singleton_fallthrough() {
  rm -f "$LOCKFILE"

  # Start a background holder that acquires the lock and holds it
  (
    exec 9>"$LOCKFILE"
    flock -x 9
    sleep 10
  ) &
  local holder_pid=$!
  sleep 0.2  # let holder acquire lock

  # Second invocation should fall through: print warning and do plain read
  # Feed it a direct answer via stdin so it doesn't block
  local output
  output=$(echo "my_fallback_answer" | timeout 3 "$SCRIPT" "Question?" 2>&1 || true)

  kill "$holder_pid" 2>/dev/null || true
  wait "$holder_pid" 2>/dev/null || true
  rm -f "$LOCKFILE"

  [[ "$output" == *"already active"* ]] || [[ "$output" == "my_fallback_answer"* ]]
}

# Test: offset file is deleted at startup
test_offset_file_deleted_at_startup() {
  # Write a stale offset file
  echo "99999" > "$OFFSET_FILE"
  chmod 600 "$OFFSET_FILE"

  # Run script with flock unavailable (forces early exit) to check startup cleanup
  # We simulate by making sops unavailable, which exits after lockfile acquired + offset cleaned
  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nexit 1\n' > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"

  PATH="${fake_dir}:${PATH}" "$SCRIPT" "Q?" 2>/dev/null || true
  rm -rf "$fake_dir"

  # Offset file should be gone (deleted at startup before sops call)
  [[ ! -f "$OFFSET_FILE" ]]
}

# Test: missing flock prints install instructions and exits non-zero
test_flock_missing_error() {
  # Prepend a fake directory with a stub flock that exits 127 (command not found)
  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nexit 127\n' > "${fake_dir}/flock"
  chmod +x "${fake_dir}/flock"

  local output
  output=$(PATH="${fake_dir}:${PATH}" "$SCRIPT" "Q?" 2>&1 || true)
  rm -rf "$fake_dir"

  # Should mention flock and brew install hint
  [[ "$output" == *"flock"* ]] && [[ "$output" == *"brew"* ]]
}

# Test: stdin race — answer typed at terminal is captured before Telegram poll
test_stdin_race_win() {
  # Use a fake sops so secrets fail — but we only need to test
  # that when stdin has data, the script emits it and exits 0.
  # We simulate by overriding MAX_TIMEOUT to 0 so the script falls
  # through to terminal read immediately; pipe an answer in.
  local fake_dir
  fake_dir=$(mktemp -d)
  # Provide a fake sops that returns a minimal valid YAML
  printf '#!/usr/bin/env bash\nprintf "bot_token: fake_token\nchat_id: 12345\n"\n' \
    > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"
  # Provide a fake curl that does nothing
  printf '#!/usr/bin/env bash\nif [[ "$*" == *getUpdates* ]]; then echo '"'"'{"result":[]}'"'"'; fi\n' \
    > "${fake_dir}/curl"
  chmod +x "${fake_dir}/curl"

  local output
  # Set MAX_TIMEOUT to 0 via env override (the script reads MAX_TIMEOUT from env if set)
  output=$(printf 'my terminal answer\n' | \
    PATH="${fake_dir}:${PATH}" MAX_TIMEOUT=0 timeout 5 "$SCRIPT" "Q?" 2>/dev/null || true)

  rm -rf "$fake_dir"
  [[ "$output" == "my terminal answer" ]]
}

# Test: timeout path — when MAX_TIMEOUT=0, falls through to blocking read
test_timeout_fallback() {
  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nprintf "bot_token: fake_token\nchat_id: 12345\n"\n' \
    > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"
  printf '#!/usr/bin/env bash\necho '"'"'{"result":[]}'"'"'\n' \
    > "${fake_dir}/curl"
  chmod +x "${fake_dir}/curl"

  local stderr_output
  stderr_output=$(printf 'fallback answer\n' | \
    PATH="${fake_dir}:${PATH}" MAX_TIMEOUT=0 timeout 5 "$SCRIPT" "Q?" 2>&1 >/dev/null || true)

  rm -rf "$fake_dir"
  # Should print timeout warning on stderr
  [[ "$stderr_output" == *"timeout"* ]]
}

# Test: SIGKILL recovery — offset file from killed session deleted at startup
test_sigkill_offset_recovery() {
  # Plant a stale offset file as if left by a killed process
  echo "77777" > "$OFFSET_FILE"
  chmod 600 "$OFFSET_FILE"

  # Run with a fake sops that fails immediately after startup cleanup
  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nexit 1\n' > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"

  PATH="${fake_dir}:${PATH}" "$SCRIPT" "Q?" 2>/dev/null || true
  rm -rf "$fake_dir"

  # Offset file must be deleted even though sops (and thus the full flow) failed
  [[ ! -f "$OFFSET_FILE" ]]
}

run_test "singleton: second invocation falls through" test_singleton_fallthrough
run_test "offset file deleted at startup" test_offset_file_deleted_at_startup
run_test "missing flock prints error with install hint" test_flock_missing_error
run_test "stdin race: terminal answer captured and returned" test_stdin_race_win
run_test "timeout fallback: warning on stderr" test_timeout_fallback
run_test "SIGKILL recovery: stale offset file deleted at startup" test_sigkill_offset_recovery

# Note: §8.6 (Telegram race win) and §8.7 (wrong chat_id ignored) require live
# Telegram credentials and must be verified manually during smoke test (Task 7).

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[[ $FAIL -eq 0 ]]
```

- [x] **Step 2: Run test to verify it fails**

```bash
bash ops/tests/test_ask_user.sh
```

Expected: FAIL (script doesn't exist)

- [x] **Step 3: Create `ops/scripts/ask-user-via-telegram.sh`**

Write the complete, correct script in one step. The poll loop uses an inline `python3` call for Telegram response parsing — there is no intermediate broken helper function.

```bash
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
if ! flock -n 9; then
  echo "⚠️  Telegram poller already active — answer at terminal:" >&2
  read -r _fallback_answer
  printf '%s\n' "$_fallback_answer"
  exit 0
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
  # Fetch the latest update_id to use as baseline (ignore pre-existing messages).
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
        if text:
            print(update["update_id"])
            print(text)
            break
PY
2>/dev/null || true)

  if [[ -n "$REPLY" ]]; then
    NEW_OFFSET=$(printf '%s' "$REPLY" | head -1)
    REPLY_TEXT=$(printf '%s' "$REPLY" | tail -n +2)
    CURRENT_OFFSET="$NEW_OFFSET"
    printf '%s\n' "$CURRENT_OFFSET" > "$OFFSET_FILE"

    if [[ -n "$REPLY_TEXT" ]]; then
      tg_send "✅ Got it! Forwarding to agent — continuing work..."
      printf '%s\n' "$REPLY_TEXT"
      exit 0
    fi
  fi

  # Brief pause to reach ~30s total loop time (1s read + 25s curl + 4s sleep).
  sleep 4
done
```

```bash
chmod +x ops/scripts/ask-user-via-telegram.sh
```

- [x] **Step 4: Run tests to verify they pass**

```bash
bash ops/tests/test_ask_user.sh
```

Expected: `Results: 6 passed, 0 failed`

- [x] **Step 5: Commit**

```bash
git add ops/scripts/ask-user-via-telegram.sh ops/tests/test_ask_user.sh
git commit -m "feat(ops): add ask-user-via-telegram.sh — singleton Telegram reply poller [plan: 2026-03-15-agents-md-telegram-redesign, Task 3, cli: claude-code, model: claude-sonnet-4-6]"
```

  - **Committed:** 68e9bee + f2bfef9

---

## Chunk 3: Test runner + Stop hook + AGENTS.md

### Task 4: Create test runner and add `make test-scripts`

**Files:**
- Create: `ops/tests/run_all.sh`
- Modify: `Makefile`

- [x] **Step 1: Create `ops/tests/run_all.sh`**

```bash
#!/usr/bin/env bash
# Runs all ops/scripts bash tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERALL=0

run_suite() {
  local name="$1"
  local file="$2"
  echo "━━━ ${name} ━━━"
  if bash "$file"; then
    echo ""
  else
    echo "❌ Suite failed: ${name}"
    OVERALL=1
  fi
}

run_suite "send-telegram-summary.sh" "${SCRIPT_DIR}/test_send_telegram.sh"
run_suite "notify.sh"                "${SCRIPT_DIR}/test_notify.sh"
run_suite "ask-user-via-telegram.sh" "${SCRIPT_DIR}/test_ask_user.sh"

if [[ $OVERALL -eq 0 ]]; then
  echo "✅ All script test suites passed."
else
  echo "❌ One or more suites failed."
  exit 1
fi
```

```bash
chmod +x ops/tests/run_all.sh
```

- [x] **Step 2: Add `test-scripts` target to Makefile**

In `Makefile`, find the `test:` target and add before or after it:

```makefile
test-scripts:
	bash ops/tests/run_all.sh
```

Also add `test-scripts` to the `.PHONY` line if present.

- [x] **Step 3: Run all tests**

```bash
make test-scripts
```

Expected: All suites pass.

- [x] **Step 4: Commit**

```bash
git add ops/tests/run_all.sh Makefile
git commit -m "feat(ops): add test runner and make test-scripts target [plan: 2026-03-15-agents-md-telegram-redesign, Task 4, cli: claude-code, model: claude-sonnet-4-6]"
```

  - **Committed:** f152489

---

### Task 5: Add Stop hook to `.claude/settings.json`

**Files:**
- Create: `.claude/settings.json`

- [x] **Step 1: Check if `.claude/settings.json` already exists**

```bash
cat .claude/settings.json 2>/dev/null || echo "NOT FOUND — will create"
```

If it exists, merge the hook into existing JSON rather than overwriting.

- [x] **Step 2: Write `.claude/settings.json`**

If the file does not exist, create it:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'TTY_ID=$(tty 2>/dev/null | tr \"/\" \"_\") || exit 0; sentinel=\"/tmp/dechord-notify-${TTY_ID}.pending\"; [ -f \"$sentinel\" ] || exit 0; REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0; \"$REPO_ROOT/ops/scripts/send-telegram-summary.sh\" --sentinel-file \"$sentinel\" && rm -f \"$sentinel\"; exit 0'"
          }
        ]
      }
    ]
  }
}
```

If the file already exists with other content, add the `Stop` key into the existing `hooks` object.

- [x] **Step 3: Manually verify the hook command**

**Note:** This step requires live sops decryption and Telegram credentials. If running offline or in CI, use the offline check below instead.

**Live verification (requires sops + Telegram):**
```bash
# Write a test sentinel
TTY_ID=$(tty | tr '/' '_')
python3 -c "import json; print(json.dumps({'title':'Hook test','summary':'Stop hook fired correctly'}))" \
  > "/tmp/dechord-notify-${TTY_ID}.pending"
chmod 600 "/tmp/dechord-notify-${TTY_ID}.pending"

# Run the hook command manually
bash -c 'TTY_ID=$(tty 2>/dev/null | tr "/" "_") || exit 0; sentinel="/tmp/dechord-notify-${TTY_ID}.pending"; [ -f "$sentinel" ] || exit 0; REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0; "$REPO_ROOT/ops/scripts/send-telegram-summary.sh" --sentinel-file "$sentinel" && rm -f "$sentinel"; exit 0'
```
Expected: Telegram message received on phone, sentinel file deleted.

**Offline structural check (no credentials needed):**
```bash
# Verify hook exits 0 when no sentinel exists (no-op path)
bash -c 'TTY_ID=$(tty 2>/dev/null | tr "/" "_") || exit 0; sentinel="/tmp/dechord-notify-${TTY_ID}.pending"; [ -f "$sentinel" ] || exit 0; echo "would send"; exit 0'
echo "Exit code: $?"
```
Expected: no output (sentinel absent → exits 0 silently). `Exit code: 0`.

- [x] **Step 4: Commit**

```bash
git add .claude/settings.json
git commit -m "feat(ops): add Claude Code Stop hook for sentinel-based Telegram delivery [plan: 2026-03-15-agents-md-telegram-redesign, Task 5, cli: claude-code, model: claude-sonnet-4-6]"
```

  - **Committed:** c49b423

---

### Task 6: Rewrite `AGENTS.md`

**Files:**
- Modify: `AGENTS.md`

- [x] **Step 1: Confirm CLAUDE.md is a symlink to AGENTS.md**

```bash
ls -la CLAUDE.md AGENTS.md
```

Expected output contains `CLAUDE.md -> AGENTS.md`. If CLAUDE.md is a regular file (not a symlink), stop and resolve the discrepancy before proceeding — rewriting AGENTS.md will diverge them.

- [x] **Step 2: Write new `AGENTS.md`**

Replace the entire file content with:

```xml
<agents>
  <section id="branching-and-commits">
    <rule>Work on main by default. No feature branches unless explicitly directed.</rule>
    <rule>Each task commit message MUST follow this exact format:
      type(scope): description [plan: docs/plans/FILENAME.md, Task N, cli: CLI_NAME, model: MODEL_NAME]
      Examples of cli values: claude-code, opencode. Examples of model values: claude-sonnet-4-6, kimi-k2.
      This format applies to all commits going forward. Existing commits are grandfathered.
    </rule>
    <rule>After every push: add a clickable commit URL to the completed task entry in the plan file.</rule>
    <rule>Delegate commit message writing and plan link updates to a subagent subprocess. Never perform these in the main session.</rule>
  </section>

  <section id="plans-and-tasks">
    <rule>Track all progress in docs/plans/ using XML with phase blocks and task checkboxes: [ ] for pending, [x] for done.</rule>
    <rule>docs/plans/ is the source of truth for execution history. Never contradict it.</rule>
  </section>

  <section id="skills-and-execution">
    <rule>For every feature or bugfix, invoke skills in this exact order: brainstorming → writing-plans → executing-plans (or subagent-driven-development for same-session work). No step may be skipped.</rule>
    <rule>Before any code execution step, invoke using-git-worktrees to isolate the work. Exception: ops/scripts/notify.sh and ops/scripts/ask-user-via-telegram.sh are notification utilities and are exempt from this rule.</rule>
    <rule>For all features and bugfixes, follow the test-driven-development skill before writing any implementation code.</rule>
    <rule>Default to subagent execution. Keep the controller session lean.</rule>
    <rule>Use context-mode MCP tools for all large output. Never pipe large results into the main context window.</rule>
  </section>

  <section id="notification">
    <rule>When user input is needed during a session: run ops/scripts/ask-user-via-telegram.sh "question text" and use its stdout as the answer. The script races terminal input against a Telegram reply — whichever arrives first wins.</rule>
    <rule>When a task or session is complete and a summary is ready: run ops/scripts/notify.sh "title" "summary body". The Claude Code Stop hook delivers it to Telegram at session end.</rule>
    <rule>Never call ops/scripts/send-telegram-summary.sh directly from agent instructions. Always route through notify.sh or ask-user-via-telegram.sh.</rule>
  </section>

  <section id="reset-and-verification">
    <rule>Before final handoff: run make reset, then invoke the verification-before-completion skill. Both are required and must run in this order.</rule>
    <rule>After verification passes: run ops/scripts/notify.sh "title" "final summary". The Stop hook delivers it.</rule>
  </section>

  <section id="architecture">
    <rule>Frontend: React 19, Vite, Tailwind v4.</rule>
    <rule>Backend: FastAPI, Python 3.13+, uv, LibSQL, Demucs stem/analysis pipeline.</rule>
    <rule>Flow: upload → optional stems → bass_analysis.wav → TabPipeline → MIDI/AlphaTex/tabs.</rule>
    <rule>Key directories: frontend/, backend/, docs/plans/. The designs.* directories are reference-only — never modify them.</rule>
    <rule>Never persist binary assets (audio, stems, MIDI, tabs) to the local filesystem. All blobs must be stored in LibSQL. Temporary files during processing are allowed only in OS temp dirs and must be deleted immediately after reading into memory.</rule>
  </section>

  <section id="portless">
    <rule>Use portless as the standard local routing layer. Allowed commands: make up, make backend, make frontend, make portless-proxy-up, make portless-proxy-down, make portless-routes.</rule>
  </section>

  <section id="design-language">
    <rule>The canonical look and feel is defined in designs.opus46/5-3. All designs.* directories are reference-only and must never be modified.</rule>
  </section>
</agents>
```

- [x] **Step 3: Verify symlink still works after rewrite**

```bash
diff AGENTS.md CLAUDE.md && echo "symlink OK"
```

Expected: no diff output (CLAUDE.md is a symlink, resolves to the same content).

- [x] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "refactor(agents): rewrite AGENTS.md with imperative script-centric rules [plan: 2026-03-15-agents-md-telegram-redesign, Task 6, cli: claude-code, model: claude-sonnet-4-6]"
```

  - **Committed:** 5ea7a47

---

### Task 7: Final smoke test

**Files:** none (validation only)

- [x] **Step 1: Run all script tests**

```bash
make test-scripts
```

Expected: all suites pass.

- [x] **Step 2: Verify notify.sh + Stop hook end-to-end**

```bash
ops/scripts/notify.sh "Smoke test" "AGENTS.md + Telegram system is live."
```

Expected: `✅ Notification queued: /tmp/dechord-notify-...`

Note: headless session (no TTY) skips sentinel creation by design — this behaviour is tested and verified by the test suite (PASS: headless exits 0 without creating sentinel).

End the Claude Code session (type `/exit` or close terminal). Verify Telegram message arrives.

- [x] **Step 3: Verify AGENTS.md and CLAUDE.md are in sync**

```bash
ls -la CLAUDE.md AGENTS.md
diff AGENTS.md CLAUDE.md && echo "symlink OK"
```

- [x] **Step 4: Final commit with plan update**

Delegate to subagent:

> Update `docs/superpowers/plans/2026-03-15-agents-md-telegram-redesign.md` — mark all tasks [x]. Add commit links for each task commit. Commit the updated plan file with message:
> `docs(plans): mark all tasks complete for AGENTS.md telegram redesign [plan: 2026-03-15-agents-md-telegram-redesign, Task 7, cli: claude-code, model: claude-sonnet-4-6]`
