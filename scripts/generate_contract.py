"""Generate OpenAPI and TypeScript deterministically; --check never modifies tracked files."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = "--check" in sys.argv
with tempfile.TemporaryDirectory(prefix="philanthra-contract-") as temporary:
    schema = Path(temporary) / "openapi.json"
    client = Path(temporary) / "schema.d.ts"
    subprocess.run(
        [
            sys.executable,
            "apps/api/manage.py",
            "spectacular",
            "--format",
            "openapi-json",
            "--file",
            str(schema),
            "--validate",
            "--fail-on-warn",
        ],
        cwd=ROOT,
        check=True,
        env={**os.environ, "PHILANTHRA_ENV": "test"},
    )
    content = json.dumps(json.loads(schema.read_text()), indent=2, sort_keys=True) + "\n"
    schema.write_text(content)
    subprocess.run(
        ["bash", "scripts/pnpm", "exec", "openapi-typescript", str(schema), "-o", str(client)],
        cwd=ROOT,
        check=True,
    )
    for source, destination in [
        (schema, ROOT / "schemas/openapi.json"),
        (client, ROOT / "packages/api-client/schema.d.ts"),
    ]:
        if CHECK:
            if not destination.exists() or source.read_bytes() != destination.read_bytes():
                raise SystemExit(
                    f"Contract drift: regenerate {destination.relative_to(ROOT)} with make api-client"
                )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
    print(
        "API contract drift check passed"
        if CHECK
        else "Generated OpenAPI and TypeScript API client types"
    )
