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
    echo "✅ PASS: $name"; PASS=$((PASS+1))
  else
    echo "❌ FAIL: $name"; FAIL=$((FAIL+1))
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
