"""Read-only prerequisites; no global environment mutation."""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def version(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def main():
    node = version(["node", "--version"])
    compose = version(["docker", "compose", "version"])
    postgres = version(
        [
            str(Path(os.getenv("PG_BIN", "/opt/homebrew/opt/postgresql@17/bin")) / "pg_ctl"),
            "--version",
        ]
    )
    postgres = postgres or version(["pg_ctl", "--version"])
    if not postgres:
        for candidate in sorted(Path("/usr/lib/postgresql").glob("*/bin/pg_ctl"), reverse=True):
            postgres = version([str(candidate), "--version"])
            if postgres:
                break
    checks = {
        "Python 3.12/3.13 (isolated environment)": version(
            [str(ROOT / ".venv/bin/python"), "--version"]
        ).startswith(("Python 3.12.", "Python 3.13.")),
        "Node 24": node.startswith("v24."),
        "pnpm": (ROOT / ".tools/node/node_modules/.bin/pnpm").exists() or shutil.which("pnpm"),
        "PostgreSQL 17+ or Docker Compose": bool(postgres or compose),
        "Installed JavaScript dependencies": (ROOT / "node_modules").exists(),
    }
    for label, value in checks.items():
        print(f"{'OK' if value else 'MISSING'}  {label}")
    print(f"Node: {node or 'unavailable'}")
    print(f"Native PostgreSQL: {postgres or 'unavailable'}")
    print(f"Docker Compose: {compose or 'unavailable; native path required'}")
    print("Run make setup for isolated dependencies. Doctor does not claim runtime readiness.")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
