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
