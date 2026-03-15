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
