#!/usr/bin/env sh
set -eu

exec bun dev -- --host "${HOST:-127.0.0.1}" --port "${PORT:-5173}"
