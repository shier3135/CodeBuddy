import asyncio
import os
from pathlib import Path

from codex_buddy import ble_transport
from codex_buddy.ble_transport import BleBuddyTransport, DiscoveredBuddy, _matches_buddy_discovery


class _FakeClient:
    def __init__(self) -> None:
        self.is_connected = True
        self.writes: list[tuple[str, bytes, bool]] = []

    async def write_gatt_char(self, uuid: str, data: bytes, response: bool) -> None:
        self.writes.append((uuid, bytes(data), response))


class _FakeNativeSession:
    def __init__(self) -> None:
        self.connected = False
        self.disconnected = False
        self.writes: list[dict] = []
        self.on_permission = None

    @property
    def is_connected(self) -> bool:
        return self.connected

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.disconnected = True

    async def write_json(self, payload: dict) -> None:
        self.writes.append(payload)

    async def emit_permission(self, request_id: str, decision: str) -> None:
        assert self.on_permission is not None
        await self.on_permission(request_id, decision)


def test_ble_transport_uses_write_with_response_for_snapshot_payloads():
    transport = BleBuddyTransport("device-1", use_native_helper=False)
    fake = _FakeClient()
    transport._client = fake

    asyncio.run(
        transport._send_json(
            {
                "total": 1,
                "running": 0,
                "waiting": 1,
                "msg": "approve: rm /tmp/demo",
                "prompt": {
                    "id": "0",
                    "tool": "Bash",
                    "hint": "rm /tmp/demo",
                },
            }
        )
    )

    assert fake.writes
    assert all(response is True for _, _, response in fake.writes)


def test_ble_transport_native_helper_connect_sends_owner_and_time_sync():
    fake = _FakeNativeSession()

    def factory(*, device_id: str, device_name: str, on_permission):
        assert device_id == "device-1"
        assert device_name == "Codex-1234"
        fake.on_permission = on_permission
        return fake

    previous_user = os.environ.get("USER")
    os.environ["USER"] = "BuddyTester"
    try:
        transport = BleBuddyTransport(
            "device-1",
            device_name="Codex-1234",
            use_native_helper=True,
            native_session_factory=factory,
        )
        asyncio.run(transport.connect())
        asyncio.run(transport.disconnect())
    finally:
        if previous_user is None:
            os.environ.pop("USER", None)
        else:
            os.environ["USER"] = previous_user

    assert fake.connected is True
    assert fake.disconnected is True
    assert fake.writes[0] == {"cmd": "owner", "name": "BuddyTester"}
    assert "time" in fake.writes[1]
    assert len(fake.writes[1]["time"]) == 2


def test_ble_transport_native_helper_forwards_permission_events():
    fake = _FakeNativeSession()
    approvals: list[tuple[str, str]] = []

    async def on_permission(request_id: str, decision: str) -> None:
        approvals.append((request_id, decision))

    def factory(*, device_id: str, device_name: str, on_permission):
        assert device_id == "device-1"
        assert device_name == "Codex-1234"
        fake.on_permission = on_permission
        return fake

    transport = BleBuddyTransport(
        "device-1",
        device_name="Codex-1234",
        on_permission=on_permission,
        use_native_helper=True,
        native_session_factory=factory,
    )

    asyncio.run(transport.connect())
    asyncio.run(fake.emit_permission("req-1", "deny"))

    assert approvals == [("req-1", "deny")]


def test_native_discovery_matches_name_or_service_uuid():
    assert _matches_buddy_discovery({"name": "Codex-4DAD", "service_uuids": []}) is True
    assert _matches_buddy_discovery({"name": "Legacy-4DAD", "service_uuids": []}) is False
    assert _matches_buddy_discovery({"name": "", "service_uuids": ["6E400001-B5A3-F393-E0A9-E50E24DCCA9E"]}) is True
    assert _matches_buddy_discovery({"name": "Other", "service_uuids": ["1234"]}) is False


def test_discover_uses_native_helper_when_backend_is_native(monkeypatch):
    expected = [DiscoveredBuddy(device_id="dev-1", name="Codex-1234")]

    monkeypatch.setenv("CODEX_BUDDY_BLE_BACKEND", "native")
    monkeypatch.setattr("codex_buddy.ble_transport._discover_with_native_helper", lambda timeout: expected)

    matches = asyncio.run(BleBuddyTransport.discover(timeout=2.5))

    assert matches == expected


def test_native_helper_app_path_prefers_runtime_install(monkeypatch, tmp_path):
    app_path = tmp_path / "CodeBuddyBLEHelper.app"
    executable = app_path / "Contents" / "MacOS" / "CodeBuddyBLEHelper"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    ble_transport._native_helper_app_path.cache_clear()
    monkeypatch.delenv("CODEX_BUDDY_BLE_HELPER_APP", raising=False)
    monkeypatch.setattr(ble_transport, "runtime_helper_app_path", lambda: Path(app_path))

    try:
        assert ble_transport._native_helper_app_path() == app_path
    finally:
        ble_transport._native_helper_app_path.cache_clear()
