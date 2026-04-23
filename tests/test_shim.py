import os
from pathlib import Path

from codex_buddy import shim


def test_shim_bypasses_codex_app_server():
    assert shim.should_bypass(["app-server"]) is True


def test_shim_bypasses_explicit_remote_sessions():
    assert shim.should_bypass(["--remote", "ws://127.0.0.1:9999"]) is True


def test_shim_extracts_workdir_from_c_flag():
    assert shim.extract_workdir(["-C", "/tmp/demo"]) == Path("/tmp/demo")


def test_shim_extracts_workdir_from_long_cd_flag():
    assert shim.extract_workdir(["--cd", "/tmp/demo"]) == Path("/tmp/demo")


def test_shim_loads_real_codex_and_execs_with_remote(monkeypatch):
    events = []

    class FakeStore:
        def __init__(self, path) -> None:
            events.append(("store_init", path))

        def load(self):
            return shim.PersistedState(setup_version=1, real_codex_path="/usr/local/bin/codex")

    async def fake_ensure_agent_running(state_path) -> None:
        events.append(("ensure_agent", state_path))

    async def fake_agent_request(state_path, payload):
        events.append(("agent_request", state_path, payload))
        return {"ok": True, "proxy_url": "ws://127.0.0.1:4567"}

    def fake_execve(path, argv, env):
        events.append(("execve", path, argv, env["CODE_BUDDY_SHIM_ACTIVE"]))
        raise SystemExit(0)

    monkeypatch.setattr(shim, "BridgeStateStore", FakeStore)
    monkeypatch.setattr(shim, "_ensure_agent_running", fake_ensure_agent_running)
    monkeypatch.setattr(shim, "_agent_request", fake_agent_request)
    monkeypatch.setattr(shim.os, "execve", fake_execve)
    monkeypatch.setattr(shim.Path, "cwd", classmethod(lambda cls: Path("/tmp/current")))

    try:
        shim.main(["--model", "gpt-5"])
    except SystemExit as exc:
        assert exc.code == 0

    assert ("ensure_agent", shim.default_state_path()) in events
    assert (
        "agent_request",
        shim.default_state_path(),
        {"cmd": "launch", "workdir": "/tmp/current"},
    ) in events
    exec_event = next(event for event in events if event[0] == "execve")
    assert exec_event[1] == "/usr/local/bin/codex"
    assert exec_event[2][:3] == ["/usr/local/bin/codex", "--remote", "ws://127.0.0.1:4567"]
    assert exec_event[2][3:] == ["--model", "gpt-5"]
    assert exec_event[3] == "1"


def test_shim_reports_missing_setup(monkeypatch, capsys):
    monkeypatch.setattr(shim, "_load_state", lambda: shim.PersistedState())
    exit_code = shim.main([])

    assert exit_code == 1
    assert "code-buddy repair" in capsys.readouterr().err
