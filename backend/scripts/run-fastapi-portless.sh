#!/usr/bin/env sh
set -eu

exec uv run fastapi dev app/main.py --host "::" --port "${PORT:-8000}"
