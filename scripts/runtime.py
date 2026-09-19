"""Canonical Compose launcher and an equivalent PostgreSQL native development path."""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
ENV = {
    **os.environ,
    "PHILANTHRA_ENV": "demo",
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "PYTHONPATH": str(ROOT / "apps/api"),
    "NEXT_TELEMETRY_DISABLED": "1",
}
PY = ROOT / ".venv/bin/python"


def run(args, **kwargs):
    subprocess.run([str(x) for x in args], cwd=ROOT, env=ENV, check=True, **kwargs)


def process_stamp(pid):
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="], capture_output=True, text=True
    )
    return result.stdout.strip()


def validate_demo_environment():
    database = urlparse(ENV.get("DATABASE_URL", "postgresql://localhost:55432/philanthra_demo"))
    if database.path != "/philanthra_demo" or database.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "Native demo requires local database philanthra_demo; refusing migrations."
        )


def owns_process(record):
    return bool(record.get("stamp")) and process_stamp(record["pid"]) == record["stamp"]


def check_port(name, port):
    path = RUNTIME / f"{name}.json"
    if path.exists() and owns_process(json.loads(path.read_text())):
        return
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except PermissionError as exc:
            raise RuntimeError(f"Permission denied checking loopback port {port}.") from exc
        except OSError as exc:
            raise RuntimeError(
                f"Port {port} is occupied by an untracked service; stop it explicitly."
            ) from exc


def start(name, args):
    path = RUNTIME / f"{name}.json"
    if path.exists():
        record = json.loads(path.read_text())
        if owns_process(record):
            return
    with (RUNTIME / f"{name}.log").open("ab") as log:
        process = subprocess.Popen(
            [str(x) for x in args],
            cwd=ROOT,
            env=ENV,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    time.sleep(0.3)
    if process.poll() is not None:
        raise RuntimeError(f"{name} exited; inspect .runtime/{name}.log")
    path.write_text(json.dumps({"pid": process.pid, "stamp": process_stamp(process.pid)}))


def wait_ready(url, seconds=90):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            with urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"Readiness timed out for {url}; inspect .runtime/*.log")


def stop():
    for name in ("web", "worker", "api"):
        path = RUNTIME / f"{name}.json"
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        if owns_process(record):
            os.killpg(record["pid"], signal.SIGTERM)
            deadline = time.monotonic() + 10
            while owns_process(record) and time.monotonic() < deadline:
                time.sleep(0.1)
            if owns_process(record):
                raise RuntimeError(f"{name} did not stop; inspect its process before retrying.")
        path.unlink()


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if action not in {"demo", "dev", "stop"}:
        raise SystemExit("Use runtime.py demo|dev|stop")
    os.umask(0o077)
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    docker = shutil.which("docker")
    if docker and os.getenv("PHILANTHRA_NATIVE") != "1":
        if action == "stop":
            run([docker, "compose", "stop"])
            return
        run([docker, "compose", "up", "--build", "-d"])
        wait_ready("http://127.0.0.1:8080/api/ready/", 180)
    else:
        if action == "stop":
            stop()
            return
        validate_demo_environment()
        check_port("api", 8000)
        check_port("web", 8080)
        if not PY.exists() or not (ROOT / "node_modules").exists():
            run(["bash", "scripts/setup.sh"])
        run(["bash", "scripts/native-db.sh"])
        run([PY, "apps/api/manage.py", "migrate", "--noinput"])
        run([PY, "apps/api/manage.py", "seed_demo"])
        if action != "dev" and not (ROOT / "apps/web/.next/BUILD_ID").exists():
            run(["bash", "scripts/pnpm", "build"])
        start(
            "api",
            [
                ROOT / ".venv/bin/gunicorn",
                "config.wsgi:application",
                "--bind",
                "127.0.0.1:8000",
                "--workers",
                "2",
                "--access-logfile",
                "/dev/null",
                "--no-control-socket",
            ],
        )
        start("worker", [PY, "apps/api/manage.py", "worker"])
        start(
            "web",
            [
                "bash",
                "scripts/pnpm",
                "--filter",
                "@philanthra/web",
                "exec",
                "next",
                "dev" if action == "dev" else "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "8080",
            ],
        )
        wait_ready("http://127.0.0.1:8080/api/ready/")
        wait_ready("http://127.0.0.1:8080/")
    print("\nPhilanthra demo ready: http://127.0.0.1:8080")
    print("Demo-only users: foundation-admin, ngo-owner, reviewer")
    print("Demo-only password: Demo-only-Philanthra-2026!")
    print("Records persist across restarts. Stop: make stop. All seeded content is fictional.")


if __name__ == "__main__":
    main()
