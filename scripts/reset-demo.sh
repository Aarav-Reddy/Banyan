#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${1:-}" != philanthra-demo ]]; then
  echo 'Refusing reset: requires make reset-demo CONFIRM=philanthra-demo.' >&2
  exit 1
fi
if command -v docker >/dev/null 2>&1 && [[ "${PHILANTHRA_NATIVE:-0}" != 1 ]]; then
  exec docker compose run --rm --no-deps api python /app/scripts/reset_demo.py "$1"
fi
exec .venv/bin/python scripts/reset_demo.py "$1"
