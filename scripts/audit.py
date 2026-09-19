"""Run both network-dependent vulnerability audits; unavailable is never a pass."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failed = False
for label, command in [
    ("Python dependency advisory service", [ROOT / ".venv/bin/pip-audit", "--local"]),
    (
        "JavaScript registry advisory service",
        ["bash", "scripts/pnpm", "audit", "--audit-level", "high"],
    ),
]:
    print(f"Network-dependent audit: {label}", flush=True)
    try:
        result = subprocess.run([str(arg) for arg in command], cwd=ROOT, timeout=180)
        if result.returncode:
            print(f"NOT PASSED: {label}; review findings or network errors above.", flush=True)
            failed = True
    except subprocess.TimeoutExpired:
        print(f"UNAVAILABLE: {label} timed out; this is not a passed audit.", flush=True)
        failed = True
sys.exit(1 if failed else 0)
