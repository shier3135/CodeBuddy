from __future__ import annotations

import asyncio
import contextlib
import functools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Optional

from bleak import BleakClient, BleakScanner

from .reducer import BuddySnapshot
from .runtime import helper_app_path as runtime_helper_app_path

NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"


@dataclass(frozen=True)
class DiscoveredBuddy:
    device_id: str
    name: str


class NativeBleHelperError(RuntimeError):
    pass


def _matches_buddy_discovery(payload: dict) -> bool:
    name = str(payload.get("name", ""))
    if name.startswith("Codex-"):
        return True
    service_uuids = {str(value).lower() for value in payload.get("service_uuids", [])}
    return NUS_SERVICE_UUID in service_uuids


def _default_use_native_helper() -> bool:
    backend = os.environ.get("CODEX_BUDDY_BLE_BACKEND", "").strip().lower()
    if backend == "bleak":
        return False
    if backend == "native":
        return True
    return sys.platform == "darwin"


@functools.lru_cache(maxsize=1)
def _native_helper_app_path() -> Path:
    override = os.environ.get("CODEX_BUDDY_BLE_HELPER_APP", "").strip()
    if override:
        app_path = Path(override).expanduser()
        executable_path = app_path / "Contents" / "MacOS" / "CodeBuddyBLEHelper"
        if not executable_path.exists():
            raise NativeBleHelperError(f"Configured helper app does not exist: {app_path}")
        return app_path

    runtime_app_path = runtime_helper_app_path()
    runtime_executable = runtime_app_path / "Contents" / "MacOS" / "CodeBuddyBLEHelper"
    if runtime_executable.exists():
        return runtime_app_path

    root = Path(__file__).resolve().parents[2]
    app_path = root / ".build" / "native" / "CodeBuddyBLEHelper.app"
    executable_path = app_path / "Contents" / "MacOS" / "CodeBuddyBLEHelper"
    source_path = root / "src" / "codex_buddy" / "native_ble_helper" / "CodeBuddyBLEHelper.swift"
    plist_path = root / "src" / "codex_buddy" / "native_ble_helper" / "Info.plist"
    build_script = root / "scripts" / "build-native-ble-helper.sh"
    needs_build = (
        not executable_path.exists()
        or executable_path.stat().st_mtime < source_path.stat().st_mtime
        or (app_path / "Contents" / "Info.plist").stat().st_mtime < plist_path.stat().st_mtime
        or executable_path.stat().st_mtime < build_script.stat().st_mtime
    )
    if needs_build:
        completed = subprocess.run(
            ["/bin/zsh", str(build_script)],
            check=True,
            capture_output=True,
            text=True,
        )
        output = completed.stdout.strip().splitlines()
        if not output:
            raise NativeBleHelperError("Native BLE helper build script returned no app path")
        app_path = Path(output[-1]).expanduser()
    if not app_path.exists():
        raise NativeBleHelperError(f"Native BLE helper app not found at {app_path}")
    return app_path


def _discover_with_native_helper(timeout: float) -> list[DiscoveredBuddy]:
    session_dir = Path(tempfile.mkdtemp(prefix="codebuddy-ble-discover-"))
    commands_dir = session_dir / "commands"
    events_path = session_dir / "events.jsonl"
    commands_dir.mkdir(parents=True, exist_ok=True)
    events_path.write_text("")

    discovered: dict[str, DiscoveredBuddy] = {}
    buffer = bytearray()

    try:
        subprocess.run(
            [
                "open",
                "-n",
                str(_native_helper_app_path()),
                "--args",
                "--session-dir",
                str(session_dir),
                "--device-id",
                "__SCAN_ONLY__",
                "--device-name",
                "",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        deadline = time.monotonic() + timeout
        offset = 0
        while time.monotonic() < deadline:
            if events_path.exists():
                with events_path.open("rb") as handle:
                    handle.seek(offset)
                    chunk = handle.read()
                if chunk:
                    offset += len(chunk)
                    buffer.extend(chunk)
                    while b"\n" in buffer:
                        line, _, rest = buffer.partition(b"\n")
                        buffer = bytearray(rest)
                        if not line:
                            continue
                        try:
                            payload = json.loads(line.decode("utf-8"))
                        except json.JSONDecodeError:
                            continue
                        if payload.get("event") != "discovered" or not _matches_buddy_discovery(payload):
                            continue
                        device_id = str(payload.get("identifier", "")).strip()
                        name = str(payload.get("name", "")).strip() or device_id
                        if device_id:
                            discovered[device_id] = DiscoveredBuddy(device_id=device_id, name=name)
            time.sleep(0.05)
    finally:
        subprocess.run(["pkill", "-f", str(session_dir)], check=False, capture_output=True, text=True)
        shutil.rmtree(session_dir, ignore_errors=True)

    matches = sorted(discovered.values(), key=lambda item: item.name)
    return matches


class NativeBleHelperSession:
    def __init__(
        self,
        *,
        device_id: str,
        device_name: str,
        on_permission: Optional[Callable[[str, str], Awaitable[None]]],
        connect_timeout: float = 15.0,
        command_timeout: float = 10.0,
    ) -> None:
        self.device_id = device_id
        self.device_name = device_name
        self.on_permission = on_permission
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout

        self._connected = False
        self._connect_error: Optional[Exception] = None
        self._session_dir: Optional[Path] = None
        self._commands_dir: Optional[Path] = None
        self._events_path: Optional[Path] = None
        self._buffer = bytearray()
        self._next_seq = 0
        self._pending: dict[int, asyncio.Future[None]] = {}
        self._pump_task: Optional[asyncio.Task[None]] = None
        self._stop_requested = False
        self._shutdown_requested = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        if self._connected:
            return
        if self._pump_task is None or self._pump_task.done():
            await self._start_helper()

        deadline = asyncio.get_running_loop().time() + self.connect_timeout
        while not self._connected:
            if self._connect_error is not None:
                raise self._connect_error
            if asyncio.get_running_loop().time() >= deadline:
                raise NativeBleHelperError("Timed out waiting for native BLE helper to connect")
            await asyncio.sleep(0.05)

    async def write_json(self, payload: dict) -> None:
        await self.connect()
        line = json.dumps(payload, separators=(",", ":"))
        await self._send_command("write_json", line=line)

    async def disconnect(self) -> None:
        if self._session_dir is None:
            return

        self._shutdown_requested = True
        if self._pump_task is not None and not self._pump_task.done():
            with contextlib.suppress(Exception):
                await self._send_command("shutdown")
            try:
                await asyncio.wait_for(self._pump_task, timeout=3.0)
            except asyncio.TimeoutError:
                self._pump_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._pump_task

        self._cleanup()

    async def _start_helper(self) -> None:
        self._cleanup()
        self._connect_error = None
        self._connected = False
        self._stop_requested = False
        self._shutdown_requested = False
        self._buffer = bytearray()

        self._session_dir = Path(tempfile.mkdtemp(prefix="codebuddy-ble-"))
        self._commands_dir = self._session_dir / "commands"
        self._events_path = self._session_dir / "events.jsonl"
        self._commands_dir.mkdir(parents=True, exist_ok=True)
        self._events_path.write_text("")

        await asyncio.to_thread(self._launch_helper_process)
        self._pump_task = asyncio.create_task(self._pump_events())

    def _launch_helper_process(self) -> None:
        assert self._session_dir is not None
        app_path = _native_helper_app_path()
        command = [
            "open",
            "-n",
            str(app_path),
            "--args",
            "--session-dir",
            str(self._session_dir),
            "--device-id",
            self.device_id,
            "--device-name",
            self.device_name,
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise NativeBleHelperError(stderr or "Failed to launch native BLE helper")

    async def _send_command(self, op: str, *, line: Optional[str] = None) -> None:
        if self._commands_dir is None:
            raise NativeBleHelperError("Native BLE helper command directory is not ready")

        self._next_seq += 1
        seq = self._next_seq
        future = asyncio.get_running_loop().create_future()
        self._pending[seq] = future

        payload: dict[str, object] = {"seq": seq, "op": op}
        if line is not None:
            payload["line"] = line

        temp_path = self._commands_dir / f"{seq:08d}.tmp"
        final_path = self._commands_dir / f"{seq:08d}.json"
        temp_path.write_text(json.dumps(payload, separators=(",", ":")))
        temp_path.replace(final_path)

        try:
            await asyncio.wait_for(future, timeout=self.command_timeout)
        finally:
            self._pending.pop(seq, None)

    async def _pump_events(self) -> None:
        offset = 0
        try:
            while not self._stop_requested:
                if self._events_path and self._events_path.exists():
                    with self._events_path.open("rb") as handle:
                        handle.seek(offset)
                        chunk = handle.read()
                    if chunk:
                        offset += len(chunk)
                        self._buffer.extend(chunk)
                        while b"\n" in self._buffer:
                            line, _, rest = self._buffer.partition(b"\n")
                            self._buffer = bytearray(rest)
                            if not line:
                                continue
                            try:
                                payload = json.loads(line.decode("utf-8"))
                            except json.JSONDecodeError:
                                continue
                            await self._handle_event(payload)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._connect_error = NativeBleHelperError(str(exc))
            self._fail_pending(self._connect_error)
            raise

    async def _handle_event(self, payload: dict) -> None:
        event = str(payload.get("event", ""))
        if event == "connected":
            self._connected = True
            self._connect_error = None
            return

        if event == "permission" and self.on_permission:
            request_id = str(payload.get("id", ""))
            decision = str(payload.get("decision", ""))
            asyncio.create_task(self.on_permission(request_id, decision))
            return

        if event == "ack":
            seq = int(payload.get("seq", -1))
            future = self._pending.get(seq)
            if future is not None and not future.done():
                future.set_result(None)
            return

        if event == "command_error":
            seq = int(payload.get("seq", -1))
            future = self._pending.get(seq)
            if future is not None and not future.done():
                future.set_exception(NativeBleHelperError(str(payload.get("message", "command failed"))))
            return

        if event == "error":
            error = NativeBleHelperError(str(payload.get("message", "native BLE helper failed")))
            self._connect_error = error
            self._fail_pending(error)
            if self._shutdown_requested:
                self._stop_requested = True
            return

        if event == "disconnected":
            error = NativeBleHelperError(str(payload.get("error", "")) or "native BLE helper disconnected")
            self._connected = False
            self._connect_error = error
            self._fail_pending(error)
            self._stop_requested = True

    def _fail_pending(self, error: Exception) -> None:
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(error)

    def _cleanup(self) -> None:
        self._stop_requested = True
        self._connected = False
        self._connect_error = None
        self._fail_pending(NativeBleHelperError("native BLE helper stopped"))
        self._pending.clear()
        self._pump_task = None
        if self._session_dir is not None:
            shutil.rmtree(self._session_dir, ignore_errors=True)
        self._session_dir = None
        self._commands_dir = None
        self._events_path = None


class BleBuddyTransport:
    def __init__(
        self,
        device_id: str,
        *,
        device_name: Optional[str] = None,
        on_permission: Optional[Callable[[str, str], Awaitable[None]]] = None,
        use_native_helper: Optional[bool] = None,
        native_session_factory: Optional[
            Callable[..., NativeBleHelperSession]
        ] = None,
    ) -> None:
        self.device_id = device_id
        self.device_name = device_name or device_id
        self.on_permission = on_permission
        self._client: Optional[BleakClient] = None
        self._buffer = bytearray()
        self._lock: Optional[asyncio.Lock] = None
        self._use_native_helper = _default_use_native_helper() if use_native_helper is None else use_native_helper
        self._native_session_factory = native_session_factory or NativeBleHelperSession
        self._native_session: Optional[NativeBleHelperSession] = None

    @classmethod
    async def discover(cls, *, timeout: float = 4.0) -> list[DiscoveredBuddy]:
        if _default_use_native_helper():
            return await asyncio.to_thread(_discover_with_native_helper, timeout)
        discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
        matches: list[DiscoveredBuddy] = []
        for _, (device, adv) in discovered.items():
            uuids = {value.lower() for value in (adv.service_uuids or [])}
            name = device.name or adv.local_name or ""
            if NUS_SERVICE_UUID in uuids or name.startswith("Codex-"):
                matches.append(DiscoveredBuddy(device_id=device.address, name=name or device.address))
        matches.sort(key=lambda item: item.name)
        return matches

    async def connect(self) -> None:
        if self._use_native_helper:
            if self._native_session is None:
                self._native_session = self._native_session_factory(
                    device_id=self.device_id,
                    device_name=self.device_name,
                    on_permission=self.on_permission,
                )
            if self._native_session.is_connected:
                return
            await self._native_session.connect()
            await self._native_session.write_json({"cmd": "owner", "name": os.environ.get("USER", "Codex")[:31]})
            await self._native_session.write_json(self._time_sync_payload())
            return

        if self._client and self._client.is_connected:
            return
        self._client = BleakClient(self.device_id)
        await self._client.connect()
        await self._client.start_notify(NUS_TX_UUID, self._handle_notification)
        await self.send_owner(os.environ.get("USER", "Codex"))
        await self.send_time_sync()

    async def disconnect(self) -> None:
        if self._use_native_helper:
            if self._native_session is not None:
                try:
                    await self._native_session.disconnect()
                finally:
                    self._native_session = None
            return

        if self._client:
            try:
                if self._client.is_connected:
                    await self._client.disconnect()
            finally:
                self._client = None

    async def send_snapshot(self, snapshot: BuddySnapshot) -> None:
        await self._send_json(snapshot.as_ble_payload())

    async def send_owner(self, owner: str) -> None:
        await self._send_json({"cmd": "owner", "name": owner[:31]})

    async def send_time_sync(self) -> None:
        await self._send_json(self._time_sync_payload())

    def _time_sync_payload(self) -> dict:
        now = datetime.now().astimezone()
        offset = int(now.utcoffset().total_seconds()) if now.utcoffset() else 0
        return {"time": [int(now.timestamp()), offset]}

    async def _send_json(self, payload: dict) -> None:
        await self.connect()
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._use_native_helper:
                assert self._native_session is not None
                await self._native_session.write_json(payload)
                return

            raw = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
            mtu = 180
            assert self._client is not None
            for idx in range(0, len(raw), mtu):
                await self._client.write_gatt_char(NUS_RX_UUID, raw[idx : idx + mtu], response=True)

    def _handle_notification(self, _: str, data: bytearray) -> None:
        self._buffer.extend(data)
        while b"\n" in self._buffer:
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            if not line:
                continue
            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            if payload.get("cmd") == "permission" and self.on_permission:
                decision = str(payload.get("decision", ""))
                request_id = str(payload.get("id", ""))
                asyncio.create_task(self.on_permission(request_id, decision))
