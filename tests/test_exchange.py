"""The request/reply exchange with the unit, against a real local WebSocket server."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import WebSocketException

from custom_components.helios_easycontrols3.EasyControls3Instance import (
    _WRITE_OK,
    DeviceTimeout,
    EasyControls3Instance,
)

module = sys.modules[EasyControls3Instance.__module__]
Handler = Callable[[ServerConnection], Awaitable[None]]


@pytest.fixture(autouse=True)
def _loopback(socket_enabled: None) -> None:
    """pytest-homeassistant blocks sockets; these tests talk to a local server."""


async def _unit(handler: Handler) -> AsyncGenerator[EasyControls3Instance]:
    async with serve(handler, "127.0.0.1", 0) as server:
        device = EasyControls3Instance("127.0.0.1")
        device._url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
        yield device


@pytest.fixture
async def silent_unit() -> AsyncGenerator[EasyControls3Instance]:
    """A unit that takes the request and never answers."""
    release = asyncio.Event()

    async def handler(ws: ServerConnection) -> None:
        await ws.recv()
        await release.wait()

    async for device in _unit(handler):
        yield device
        release.set()


@pytest.fixture
async def acking_unit() -> AsyncGenerator[EasyControls3Instance]:
    async def handler(ws: ServerConnection) -> None:
        await ws.recv()
        await ws.send(_WRITE_OK)

    async for device in _unit(handler):
        yield device


async def test_silent_unit_times_out(
    monkeypatch: pytest.MonkeyPatch, silent_unit: EasyControls3Instance
) -> None:
    """Without a bound the read hangs forever; the 5 s guard fails the test then."""
    monkeypatch.setattr(module, "_EXCHANGE_TIMEOUT", 0.2, raising=False)
    with pytest.raises(DeviceTimeout, match="no reply"):
        await asyncio.wait_for(silent_unit.readCurrentData(), 5)


async def test_timeout_releases_the_lock(
    monkeypatch: pytest.MonkeyPatch, silent_unit: EasyControls3Instance
) -> None:
    """A stuck exchange must not leave later writes queued behind the lock."""
    monkeypatch.setattr(module, "_EXCHANGE_TIMEOUT", 0.2, raising=False)
    with pytest.raises(DeviceTimeout):
        await asyncio.wait_for(silent_unit.readCurrentData(), 5)
    assert not silent_unit._lock.locked()


@pytest.fixture
async def text_unit() -> AsyncGenerator[EasyControls3Instance]:
    """A server that answers with a text frame, not a binary one."""

    async def handler(ws: ServerConnection) -> None:
        await ws.recv()
        await ws.send("hello")

    async for device in _unit(handler):
        yield device


async def test_text_frame_is_a_typed_error(text_unit: EasyControls3Instance) -> None:
    with pytest.raises(WebSocketException, match="text frame"):
        await text_unit._exchangeData(b"\x00")


async def test_text_frame_reads_as_cannot_connect(
    text_unit: EasyControls3Instance,
) -> None:
    """test_connection returning False is what the config flow shows as cannot_connect."""
    assert await text_unit.test_connection() is False


async def test_answering_unit_is_unaffected(acking_unit: EasyControls3Instance) -> None:
    assert await acking_unit._exchangeData(b"\x00") == _WRITE_OK
