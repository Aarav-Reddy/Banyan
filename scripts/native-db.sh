#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
umask 077
PG_BIN="${PG_BIN:-/opt/homebrew/opt/postgresql@17/bin}"
if [[ ! -x "$PG_BIN/initdb" ]]; then
  PG_BIN="$(dirname "$(command -v initdb || true)")"
fi
if [[ ! -x "$PG_BIN/initdb" ]]; then
  echo 'PostgreSQL 17 binaries required. macOS: brew install postgresql@17; Linux: install PostgreSQL 17.' >&2
  exit 1
fi
mkdir -p .runtime
chmod 700 .runtime
if [[ ! -f .runtime/pg/PG_VERSION ]]; then
  printf '%s\n' 'philanthra-local' > .runtime/pg-password
  chmod 600 .runtime/pg-password
  "$PG_BIN/initdb" -D "$ROOT/.runtime/pg" -U philanthra --pwfile="$ROOT/.runtime/pg-password" --auth=scram-sha-256 --encoding=UTF8 --locale=C
fi
if ! "$PG_BIN/pg_ctl" -D "$ROOT/.runtime/pg" status >/dev/null 2>&1; then
  "$PG_BIN/pg_ctl" -D "$ROOT/.runtime/pg" -l "$ROOT/.runtime/postgres.log" -o "-h 127.0.0.1 -p 55432 -k '$ROOT/.runtime'" start -w
fi
export PGPASSWORD=philanthra-local
if ! "$PG_BIN/psql" -h 127.0.0.1 -p 55432 -U philanthra -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='philanthra_demo'" | grep -q 1; then
  "$PG_BIN/createdb" -h 127.0.0.1 -p 55432 -U philanthra philanthra_demo
fi
echo 'Project-local PostgreSQL ready at 127.0.0.1:55432 (philanthra_demo).'
