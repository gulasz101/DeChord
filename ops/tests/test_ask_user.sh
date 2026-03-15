#!/usr/bin/env bash
# Tests for ask-user-via-telegram.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT="${OPS_DIR}/scripts/ask-user-via-telegram.sh"
PASS=0; FAIL=0

# Ensure flock is on PATH (installed via util-linux from homebrew but may not be linked)
FLOCK_BREW_PATH="/opt/homebrew/opt/util-linux/bin"
if [[ -x "${FLOCK_BREW_PATH}/flock" ]]; then
  export PATH="${FLOCK_BREW_PATH}:${PATH}"
fi

run_test() {
  local name="$1"; shift
  if "$@" 2>/dev/null; then
    echo "✅ PASS: $name"; PASS=$((PASS+1))
  else
    echo "❌ FAIL: $name"; FAIL=$((FAIL+1))
  fi
}

# Derive lock path that script will use
TTY_ID=$(tty 2>/dev/null | tr '/' '_') || TTY_ID="notty"
LOCKFILE="/tmp/dechord-telegram-ask-${TTY_ID}.lock"
OFFSET_FILE="/tmp/dechord-telegram-offset-${TTY_ID}.txt"

# Cleanup after each test
cleanup() {
  rm -f "$LOCKFILE" "$OFFSET_FILE"
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
  local output
  output=$(echo "my_fallback_answer" | timeout 3 "$SCRIPT" "Question?" 2>&1 || true)

  kill "$holder_pid" 2>/dev/null || true
  wait "$holder_pid" 2>/dev/null || true
  rm -f "$LOCKFILE"

  [[ "$output" == *"already active"* ]] || [[ "$output" == "my_fallback_answer"* ]]
}

# Test: offset file is deleted at startup
test_offset_file_deleted_at_startup() {
  echo "99999" > "$OFFSET_FILE"
  chmod 600 "$OFFSET_FILE"

  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nexit 1\n' > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"

  PATH="${fake_dir}:${PATH}" "$SCRIPT" "Q?" 2>/dev/null || true
  rm -rf "$fake_dir"

  [[ ! -f "$OFFSET_FILE" ]]
}

# Test: missing flock prints install instructions and exits non-zero
test_flock_missing_error() {
  local fake_dir
  fake_dir=$(mktemp -d)
  # Strip util-linux from PATH so flock is not found, but keep all other tools
  local no_flock_path
  no_flock_path=$(printf '%s' "$PATH" | tr ':' '\n' | grep -v 'util-linux' | tr '\n' ':' | sed 's/:$//')
  local output
  output=$(PATH="${fake_dir}:${no_flock_path}" "$SCRIPT" "Q?" 2>&1 || true)
  rm -rf "$fake_dir"

  [[ "$output" == *"flock"* ]] && [[ "$output" == *"brew"* ]]
}

# Test: stdin race — answer typed at terminal is captured
test_stdin_race_win() {
  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nprintf "bot_token: fake_token\nchat_id: 12345\n"\n' \
    > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"
  printf '#!/usr/bin/env bash\nif [[ "$*" == *getUpdates* ]]; then echo '"'"'{"result":[]}'"'"'; fi\n' \
    > "${fake_dir}/curl"
  chmod +x "${fake_dir}/curl"

  local output
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
  [[ "$stderr_output" == *"timeout"* ]]
}

# Test: SIGKILL recovery — offset file from killed session deleted at startup
test_sigkill_offset_recovery() {
  echo "77777" > "$OFFSET_FILE"
  chmod 600 "$OFFSET_FILE"

  local fake_dir
  fake_dir=$(mktemp -d)
  printf '#!/usr/bin/env bash\nexit 1\n' > "${fake_dir}/sops"
  chmod +x "${fake_dir}/sops"

  PATH="${fake_dir}:${PATH}" "$SCRIPT" "Q?" 2>/dev/null || true
  rm -rf "$fake_dir"

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
