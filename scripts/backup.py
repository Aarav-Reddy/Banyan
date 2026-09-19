"""Local demo backup and isolated PostgreSQL restore verification; never overwrites a database."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv(
    "DATABASE_URL", "postgresql://philanthra:philanthra-local@127.0.0.1:55432/philanthra_demo"
)
parsed = urlparse(URL)
if parsed.path != "/philanthra_demo" or parsed.hostname not in {"127.0.0.1", "localhost", "db"}:
    raise SystemExit("This helper is limited to the known local philanthra_demo database.")
BIN = Path(os.getenv("PG_BIN", "/opt/homebrew/opt/postgresql@17/bin"))


def binary(name):
    path = BIN / name
    return str(path) if path.exists() else shutil.which(name) or name


def command(name, database, *args):
    env = {**os.environ, "PGPASSWORD": parsed.password or ""}
    cmd = [
        binary(name),
        "-h",
        parsed.hostname,
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username,
    ]
    cmd += ["--dbname", database] if name in {"pg_dump", "pg_restore"} else []
    subprocess.run([*cmd, *args], env=env, cwd=ROOT, check=True, capture_output=True)


def connection_options(database):
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": database,
    }


def digest_connection(conn):
    result = {}
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = [row[0] for row in cur.fetchall()]
        for table in tables:
            cur.execute(
                sql.SQL(
                    "SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text"
                ).format(sql.Identifier(table))
            )
            rows = [row[0] for row in cur.fetchall()]
            result[table] = {
                "count": len(rows),
                "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
            }
    return result


def digest(database):
    with psycopg.connect(**connection_options(database)) as conn:
        return digest_connection(conn)


def main():
    if sys.argv[1:] not in (["create"], ["verify"]):
        raise SystemExit("Use backup.py create|verify")
    os.umask(0o077)
    directory = ROOT / ".runtime/backups"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    filename = directory / f"philanthra-demo-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}.dump"
    # Both row hashes and pg_dump read one PostgreSQL snapshot even if writers are active.
    with psycopg.connect(**connection_options("philanthra_demo")) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        snapshot = conn.execute("SELECT pg_export_snapshot()").fetchone()[0]
        before = digest_connection(conn)
        command(
            "pg_dump",
            "philanthra_demo",
            "--snapshot",
            snapshot,
            "--format=custom",
            "--file",
            str(filename),
        )
    filename.chmod(0o600)
    if sys.argv[1:] == ["create"]:
        print(f"Local backup written: {filename.relative_to(ROOT)} (private; never commit)")
        return
    scratch = f"philanthra_restore_verify_{os.getpid()}"
    command("createdb", "", scratch)
    try:
        command(
            "pg_restore", scratch, "--no-owner", "--no-privileges", "--exit-on-error", str(filename)
        )
        after = digest(scratch)
        if before != after:
            raise RuntimeError("Restored table contents differ from source snapshot")
        evidence = {
            "status": "passed",
            "tables": len(after),
            "rows": sum(x["count"] for x in after.values()),
            "checked_at": datetime.now(UTC).isoformat(),
            "scope": "Isolated local PostgreSQL restore; full row hashes compared.",
        }
        (ROOT / ".runtime/restore-evidence.json").write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence))
    finally:
        # Only the fresh, uniquely named scratch database created above is dropped.
        command("dropdb", "", scratch)


if __name__ == "__main__":
    main()
