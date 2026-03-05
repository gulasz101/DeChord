#!/usr/bin/env sh
set -eu

exec uv run fastapi dev app/main.py --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
