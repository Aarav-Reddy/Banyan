#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .tools
.tools/bin/python -m pip install uv==0.12.17
.tools/bin/uv sync --frozen --cache-dir .cache/uv
npm install --prefix .tools/node pnpm@12.4.2
bash scripts/pnpm install --frozen-lockfile
echo 'Dependencies installed. make demo uses Docker Compose when available, otherwise project-local PostgreSQL.'
