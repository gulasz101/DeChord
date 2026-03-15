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
    echo "✅ PASS: $name"; PASS=$((PASS+1))
  else
    echo "❌ FAIL: $name"; FAIL=$((FAIL+1))
  fi
}

# Mock environment: override secrets file with a fake one
export TELEGRAM_SECRETS_FILE="/dev/null"

# Test: --sentinel-file with valid JSON extracts title and summary
test_sentinel_file_parsing() {
  local sentinel
  sentinel=$(mktemp)
  printf '{"title":"Test Title","summary":"Test body"}' > "$sentinel"
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
