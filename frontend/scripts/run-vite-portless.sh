#!/usr/bin/env sh
set -eu

exec bun dev -- --host "::" --port "${PORT:-5173}"
