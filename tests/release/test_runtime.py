"""Release safeguards are checked without altering a running demo."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_runtime", ROOT / "scripts/runtime.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost:55432/customer_records",
        "postgresql://production.example/philanthra_demo",
        "postgresql://db/philanthra_demo",
    ],
)
def test_native_demo_rejects_unowned_database(monkeypatch, url):
    monkeypatch.setitem(runtime.ENV, "DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="refusing migrations"):
        runtime.validate_demo_environment()


def test_native_demo_accepts_known_local_database(monkeypatch):
    monkeypatch.setitem(runtime.ENV, "DATABASE_URL", "postgresql://127.0.0.1:55432/philanthra_demo")
    runtime.validate_demo_environment()


def test_empty_process_stamp_cannot_authorize_signaling(monkeypatch):
    monkeypatch.setattr(runtime, "process_stamp", lambda _pid: "")
    assert not runtime.owns_process({"pid": 123, "stamp": ""})


def test_reused_pid_cannot_authorize_signaling(monkeypatch):
    monkeypatch.setattr(runtime, "process_stamp", lambda _pid: "new start time unrelated command")
    assert not runtime.owns_process({"pid": 123, "stamp": "old start time owned command"})


def test_matching_nonempty_identity_authorizes_owned_process(monkeypatch):
    monkeypatch.setattr(runtime, "process_stamp", lambda _pid: "same start time owned command")
    assert runtime.owns_process({"pid": 123, "stamp": "same start time owned command"})


def test_invalid_command_cannot_start_services(monkeypatch):
    monkeypatch.setattr(runtime.sys, "argv", ["runtime.py", "reset"])
    with pytest.raises(SystemExit, match="demo\\|dev\\|stop"):
        runtime.main()


def test_port_check_rejects_live_listener_but_allows_immediate_restart(monkeypatch, tmp_path):
    import socket

    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen(1)
        with pytest.raises(RuntimeError, match="occupied by an untracked service"):
            runtime.check_port("isolated-test", port)
        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            accepted, _ = listener.accept()
            with accepted:
                accepted.shutdown(socket.SHUT_WR)
                assert client.recv(1) == b""
    # The previous server-side connection may still be in TCP TIME_WAIT.
    runtime.check_port("isolated-test", port)
