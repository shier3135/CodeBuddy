import argparse
import asyncio
import io
import json
from typing import Optional

import pytest

from codex_buddy import cli


def test_main_runs_setup_when_no_subcommand_and_setup_incomplete(monkeypatch):
    seen: dict[str, object] = {}

    def fake_is_setup_complete(args: argparse.Namespace) -> bool:
        seen["checked_state_path"] = args.state_path
        return False

    def fake_setup(args: argparse.Namespace) -> int:
        seen["command"] = args.command
        seen["state_path"] = args.state_path
        return 7

    monkeypatch.setattr(cli, "_is_setup_complete", fake_is_setup_complete)
    monkeypatch.setattr(cli, "_setup", fake_setup)

    exit_code = cli.main([])

    assert exit_code == 7
    assert seen == {
        "checked_state_path": cli.default_state_path(),
        "command": "default",
        "state_path": cli.default_state_path(),
    }


def test_main_shows_status_when_no_subcommand_and_setup_complete(monkeypatch):
    events = []

    def fake_is_setup_complete(args: argparse.Namespace) -> bool:
        events.append(("is_setup_complete", args.state_path))
        return True

    def fake_default_status(args: argparse.Namespace) -> int:
        events.append(("default_status", args.state_path, args.command))
        return 11

    monkeypatch.setattr(cli, "_is_setup_complete", fake_is_setup_complete)
    monkeypatch.setattr(cli, "_default_status", fake_default_status)

    exit_code = cli.main([])

    assert exit_code == 11
    assert events == [
        ("is_setup_complete", cli.default_state_path()),
        ("default_status", cli.default_state_path(), "default"),
    ]


def test_pair_resends_time_sync_before_disconnect(monkeypatch):
    events: list[object] = []

    class FakeTransport:
        def __init__(self, device_id: str, *, device_name: Optional[str] = None, **_: object) -> None:
            events.append(("init", device_id, device_name))

        @classmethod
        async def discover(cls, *, timeout: float = 4.0):
            events.append(("discover", timeout))
            return [argparse.Namespace(device_id="dev-1", name="Codex-1234")]

        async def connect(self) -> None:
            events.append("connect")

        async def send_time_sync(self) -> None:
            events.append("time_sync")

        async def disconnect(self) -> None:
            events.append("disconnect")

    class FakeStore:
        def __init__(self, path) -> None:
            events.append(("store_init", path))

        def load(self):
            return cli.PersistedState(tokens_today=3, tokens_date="2026-04-20", tokens_total=9)

        def save(self, state) -> None:
            events.append(("save", state.paired_device_id, state.paired_device_name, state.tokens_today, state.tokens_total))

    async def fake_sleep(seconds: float) -> None:
        events.append(("sleep", seconds))

    monkeypatch.setattr(cli, "BleBuddyTransport", FakeTransport)
    monkeypatch.setattr(cli, "BridgeStateStore", FakeStore)
    monkeypatch.setattr(cli.asyncio, "sleep", fake_sleep)

    args = argparse.Namespace(
        state_path="/tmp/codebuddy-state.json",
        device=None,
        timeout=4.0,
        command="pair",
    )

    exit_code = asyncio.run(cli._pair(args))

    assert exit_code == 0
    assert ("discover", 4.0) in events
    assert ("init", "dev-1", "Codex-1234") in events
    assert "connect" in events
    assert "time_sync" in events
    assert ("sleep", 0.25) in events
    assert "disconnect" in events


def test_pair_prompts_for_choice_when_multiple_devices_found(monkeypatch):
    events: list[object] = []

    class FakeTransport:
        def __init__(self, device_id: str, *, device_name: Optional[str] = None, **_: object) -> None:
            events.append(("init", device_id, device_name))

        @classmethod
        async def discover(cls, *, timeout: float = 4.0):
            return [
                argparse.Namespace(device_id="dev-1", name="Codex-1111"),
                argparse.Namespace(device_id="dev-2", name="Codex-2222"),
            ]

        async def connect(self) -> None:
            events.append("connect")

        async def send_time_sync(self) -> None:
            events.append("time_sync")

        async def disconnect(self) -> None:
            events.append("disconnect")

    class FakeStore:
        def __init__(self, path) -> None:
            pass

        def load(self):
            return cli.PersistedState()

        def save(self, state) -> None:
            events.append(("saved", state.paired_device_id, state.paired_device_name))

    async def fake_sleep(seconds: float) -> None:
        events.append(("sleep", seconds))

    monkeypatch.setattr(cli, "BleBuddyTransport", FakeTransport)
    monkeypatch.setattr(cli, "BridgeStateStore", FakeStore)
    monkeypatch.setattr(cli.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr("builtins.input", lambda _: "2")

    args = argparse.Namespace(
        state_path="/tmp/codebuddy-state.json",
        device=None,
        timeout=4.0,
        command="pair",
    )

    exit_code = asyncio.run(cli._pair(args))

    assert exit_code == 0
    assert ("init", "dev-2", "Codex-2222") in events
    assert ("saved", "dev-2", "Codex-2222") in events


def test_run_uses_agent_launch_and_executes_local_codex_remote(monkeypatch):
    events: list[object] = []

    class FakeStore:
        def __init__(self, path) -> None:
            events.append(("store_init", path))

        def load(self):
            return cli.PersistedState(paired_device_id="dev-1", paired_device_name="Codex-1234")

    async def fake_ensure_agent_running(state_path) -> None:
        events.append(("ensure_agent", state_path))

    async def fake_agent_request(state_path, payload):
        events.append(("agent_request", state_path, payload))
        return {"ok": True, "proxy_url": "ws://127.0.0.1:4567"}

    class FakeProcess:
        async def wait(self) -> int:
            return 23

    async def fake_create_subprocess_exec(*command, **kwargs):
        events.append(("spawn", command, kwargs))
        return FakeProcess()

    monkeypatch.setattr(cli, "BridgeStateStore", FakeStore)
    monkeypatch.setattr(cli, "_ensure_agent_running", fake_ensure_agent_running)
    monkeypatch.setattr(cli, "_agent_request", fake_agent_request)
    monkeypatch.setattr(cli.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    args = argparse.Namespace(
        state_path="/tmp/codebuddy-state.json",
        workdir=cli.Path("/tmp/demo"),
        prompt="Inspect this project",
        command="run",
    )

    exit_code = asyncio.run(cli._run(args))

    assert exit_code == 23
    assert ("ensure_agent", "/tmp/codebuddy-state.json") in events
    assert (
        "agent_request",
        "/tmp/codebuddy-state.json",
        {"cmd": "launch", "workdir": "/tmp/demo"},
    ) in events
    spawn = next(item for item in events if item[0] == "spawn")
    assert spawn[1] == (
        "codex",
        "--remote",
        "ws://127.0.0.1:4567",
        "-a",
        "untrusted",
        "-C",
        "/tmp/demo",
        "Inspect this project",
    )


def test_status_prefers_live_agent_status(monkeypatch, capsys):
    def fake_agent_status(state_path):
        assert state_path == "/tmp/codebuddy-state.json"
        return {
            "ok": True,
            "state": {
                "agent_running": True,
                "buddy_connected": True,
                "snapshot": {"total": 1, "running": 1, "waiting": 0, "msg": "working"},
            },
        }

    monkeypatch.setattr(cli, "_agent_status", fake_agent_status)

    exit_code = cli._status(argparse.Namespace(state_path="/tmp/codebuddy-state.json"))

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_running"] is True
    assert payload["snapshot"]["msg"] == "working"


def test_help_only_surfaces_public_user_commands(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "doctor" in output
    assert "repair" in output
    assert "uninstall" in output
    assert "agent" not in output
    assert "service-install" not in output
    assert "sessions" not in output
