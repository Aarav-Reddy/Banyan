"""Real, isolated PostgreSQL/API/worker/web fixture for browser and smoke verification."""

import contextlib
import http.client
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv/bin/python"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_ready(url, processes):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("An E2E service exited; inspect .runtime/e2e-*/ logs.")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"E2E readiness timed out: {url}")


def proxy_handler(api_port, web_port):
    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log request bodies, query strings, or private resource identifiers.

        def proxy(self):
            port = api_port if self.path.startswith("/api/") else web_port
            hop = {"connection", "transfer-encoding", "keep-alive", "upgrade"}
            headers = {key: value for key, value in self.headers.items() if key.lower() not in hop}
            length = int(self.headers.get("Content-Length", "0"))
            if length > 6 * 1024 * 1024:
                self.send_error(413)
                return
            body = self.rfile.read(length) if length else None
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=45)
            try:
                connection.request(self.command, self.path, body=body, headers=headers)
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in hop | {"content-length"}:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if self.command != "HEAD":
                    try:
                        self.wfile.write(data)
                    except (BrokenPipeError, ConnectionResetError):
                        pass  # Browser navigated away; response was already produced.
            finally:
                connection.close()

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = proxy

    return Proxy


def main():
    os.umask(0o077)
    original = urlsplit(
        os.getenv(
            "DATABASE_URL",
            "postgresql://philanthra:philanthra-local@127.0.0.1:55432/philanthra_demo",
        )
    )
    if original.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("E2E fixture requires an explicitly local PostgreSQL service.")
    database = "philanthra_e2e_" + uuid.uuid4().hex
    database_url = urlunsplit(original._replace(path="/" + database))
    admin_url = urlunsplit(original._replace(path="/postgres"))
    directory = ROOT / ".runtime" / database.replace("philanthra_", "")
    directory.mkdir(parents=True, mode=0o700)
    api_port, web_port = free_port(), free_port()
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "PHILANTHRA_ENV": "test",
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "PYTHONPATH": str(ROOT / "apps/api"),
        "PHILANTHRA_LLM_PROVIDER": "none",
        "CSRF_TRUSTED_ORIGINS": "http://127.0.0.1:8081",
        "ALLOWED_HOSTS": "127.0.0.1,localhost",
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    processes = []
    server = None
    created = False
    stopped = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopped.set())

    def run(args):
        subprocess.run([str(arg) for arg in args], cwd=ROOT, env=env, check=True)

    def start(name, args):
        with (directory / f"{name}.log").open("wb") as log:
            processes.append(
                subprocess.Popen(
                    [str(arg) for arg in args],
                    cwd=ROOT,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
            )

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        created = True
        run([PY, "apps/api/manage.py", "migrate", "--noinput"])
        run(
            [
                PY,
                "apps/api/manage.py",
                "shell",
                "-c",
                "from philanthra.demo.seed import seed_demo; print(seed_demo())",
            ]
        )
        # Process real seed events before timing interactive browser journeys.
        # This runs the same leased worker and persists its actual outputs.
        run([PY, "apps/api/manage.py", "worker", "--drain"])
        run(
            [
                PY,
                "apps/api/manage.py",
                "shell",
                "-c",
                "from philanthra.core.models import Job; assert not Job.objects.exclude(state__in=['completed','canceled']).exists(), 'Seed jobs did not finish successfully'",
            ]
        )
        start(
            "api",
            [
                ROOT / ".venv/bin/gunicorn",
                "config.wsgi:application",
                "--bind",
                f"127.0.0.1:{api_port}",
                "--workers",
                "2",
                "--no-control-socket",
                "--access-logfile",
                "/dev/null",
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
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(web_port),
            ],
        )
        wait_ready(f"http://127.0.0.1:{api_port}/api/ready/", processes)
        wait_ready(f"http://127.0.0.1:{web_port}/", processes)
        server = ThreadingHTTPServer(("127.0.0.1", 8081), proxy_handler(api_port, web_port))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print("Isolated real-backend test fixture ready at http://127.0.0.1:8081", flush=True)
        if sys.argv[1:] == ["--smoke"]:
            subprocess.run(
                [str(PY), "scripts/smoke.py"],
                cwd=ROOT,
                check=True,
                env={**env, "PHILANTHRA_BASE_URL": "http://127.0.0.1:8081"},
            )
        else:
            while not stopped.wait(0.5):
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("An E2E service exited during testing.")
    finally:
        if server:
            server.shutdown()
            server.server_close()
        for process in reversed(processes):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        if created:
            with psycopg.connect(admin_url, autocommit=True) as conn:
                conn.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database))
                )


if __name__ == "__main__":
    main()
