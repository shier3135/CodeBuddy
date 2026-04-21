from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from .agent import AgentClient, AgentClientError, default_socket_path, spawn_agent_process, wait_for_agent
from .bridge import default_state_path
from .state_store import BridgeStateStore, PersistedState


def should_bypass(argv: list[str], *, environ: Optional[dict[str, str]] = None) -> bool:
    environ = os.environ if environ is None else environ
    if environ.get("CODE_BUDDY_BYPASS") == "1":
        return True
    if environ.get("CODE_BUDDY_SHIM_ACTIVE") == "1":
        return True
    if argv and argv[0] == "app-server":
        return True
    return "--remote" in argv


def extract_workdir(argv: list[str]) -> Optional[Path]:
    for index, arg in enumerate(argv):
        if arg in {"-C", "--cd"} and index + 1 < len(argv):
            return Path(argv[index + 1]).expanduser()
        if arg.startswith("--cd="):
            return Path(arg.split("=", 1)[1]).expanduser()
    return None


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if should_bypass(argv):
        return _exec_real_codex(_load_state(), argv)

    state = _load_state()
    if state.setup_version <= 0 or not state.real_codex_path:
        print("Code Buddy setup is incomplete. Run `code-buddy repair` first.", file=sys.stderr)
        return 1
    if not Path(state.real_codex_path).exists():
        print("Saved Codex executable is missing. Run `code-buddy repair` first.", file=sys.stderr)
        return 1

    workdir = extract_workdir(argv) or Path.cwd()
    state_path = default_state_path()
    asyncio.run(_ensure_agent_running(state_path))
    response = asyncio.run(_agent_request(state_path, {"cmd": "launch", "workdir": str(workdir)}))
    proxy_url = str(response["proxy_url"])
    return _exec_real_codex(state, ["--remote", proxy_url, *argv])


def _load_state() -> PersistedState:
    return BridgeStateStore(default_state_path()).load()


def _exec_real_codex(state: PersistedState, argv: list[str]) -> int:
    real_codex = state.real_codex_path or shutil_which_codex()
    if not real_codex:
        print("Unable to locate the real `codex` executable. Run `code-buddy repair` first.", file=sys.stderr)
        return 1
    env = os.environ.copy()
    env["CODE_BUDDY_SHIM_ACTIVE"] = "1"
    os.execve(real_codex, [real_codex, *argv], env)
    return 0


def shutil_which_codex() -> str:
    for path_entry in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path_entry).expanduser() / "codex"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


async def _ensure_agent_running(state_path: Path) -> None:
    socket_path = default_socket_path(state_path)
    client = AgentClient(socket_path)
    try:
        await client.request({"cmd": "ping"})
        return
    except AgentClientError:
        spawn_agent_process(state_path)
        await wait_for_agent(socket_path)


async def _agent_request(state_path: Path, payload: dict[str, object]) -> dict[str, object]:
    client = AgentClient(default_socket_path(state_path))
    return await client.request(payload)
