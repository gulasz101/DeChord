#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ops/scripts/send-telegram-summary.sh [--title TITLE] [--summary-file PATH] [--skip]

Options:
  --title TITLE         Override the message title.
  --summary-file PATH   Read the summary body from PATH.
  --sentinel-file PATH  Read title and summary from a JSON sentinel file.
  --skip                Exit successfully without sending anything.
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

parse_yaml_value() {
  local key="$1"
  local content="$2"

  python3 - "$key" "$content" <<'PY'
import re
import sys

key = sys.argv[1]
text = sys.argv[2]
pattern = rf'^\s*{re.escape(key)}:\s*["\']?([^"\n\']+)["\']?\s*$'
match = re.search(pattern, text, re.MULTILINE)
if not match:
    raise SystemExit(f"Missing key: {key}")
print(match.group(1))
PY
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${OPS_DIR}/.." && pwd)"
DEFAULT_TITLE="Codex finished work"
SUMMARY_FILE=""
SKIP_SEND=0
TITLE="${DEFAULT_TITLE}"
SENTINEL_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)
      TITLE="${2:?Missing value for --title}"
      shift 2
      ;;
    --summary-file)
      SUMMARY_FILE="${2:?Missing value for --summary-file}"
      shift 2
      ;;
    --skip)
      SKIP_SEND=1
      shift
      ;;
    --sentinel-file)
      SENTINEL_FILE="${2:?Missing value for --sentinel-file}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

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

if [[ "${SKIP_SEND}" -eq 1 ]]; then
  echo "Telegram summary skipped."
  exit 0
fi

if [[ -n "${SUMMARY_FILE}" ]]; then
  SUMMARY="$(<"${SUMMARY_FILE}")"
elif [[ ! -t 0 ]]; then
  SUMMARY="$(cat)"
else
  echo "Provide --summary-file PATH or pipe the summary on stdin." >&2
  exit 1
fi

if [[ -z "${SUMMARY}" ]]; then
  echo "Summary body is empty." >&2
  exit 1
fi

require_command sops
require_command curl
require_command python3

if [[ -z "${SOPS_AGE_KEY_FILE:-}" && -f "${HOME}/.config/sops/age/keys.txt" ]]; then
  export SOPS_AGE_KEY_FILE="${HOME}/.config/sops/age/keys.txt"
fi

SECRETS_FILE="${TELEGRAM_SECRETS_FILE:-${OPS_DIR}/secrets/telegram.sops.yaml}"

if [[ ! -f "${SECRETS_FILE}" ]]; then
  echo "Secrets file not found: ${SECRETS_FILE}" >&2
  exit 1
fi

DECRYPTED_SECRETS="$(sops -d "${SECRETS_FILE}")"
BOT_TOKEN="$(parse_yaml_value "bot_token" "${DECRYPTED_SECRETS}")"
CHAT_ID="$(parse_yaml_value "chat_id" "${DECRYPTED_SECRETS}")"

REPO_NAME="$(basename "${REPO_ROOT}")"
BRANCH_NAME="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"

MESSAGE="$(cat <<EOF
${TITLE}
Repo: ${REPO_NAME}
Branch: ${BRANCH_NAME}

${SUMMARY}
EOF
)"

curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MESSAGE}" \
  >/dev/null

echo "Telegram summary sent to chat ${CHAT_ID}."
