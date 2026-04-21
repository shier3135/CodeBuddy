from __future__ import annotations

from pathlib import Path


def legacy_runtime_root() -> Path:
    return Path.home() / ".codex-buddy"


def runtime_root() -> Path:
    return Path.home() / ".code-buddy"


def state_path() -> Path:
    return runtime_root() / "state.json"


def logs_dir() -> Path:
    return runtime_root() / "logs"


def shim_dir() -> Path:
    return runtime_root() / "bin"


def shim_path() -> Path:
    return shim_dir() / "codex"


def helper_dir() -> Path:
    return runtime_root() / "helper"


def helper_app_path() -> Path:
    return helper_dir() / "CodeBuddyBLEHelper.app"


def socket_path() -> Path:
    return runtime_root() / "agent.sock"


def zprofile_path() -> Path:
    return Path.home() / ".zprofile"
