"""Config flow: initial setup."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant.common import MockConfigEntry

from custom_components.helios_easycontrols3.const import DOMAIN
from custom_components.helios_easycontrols3.EasyControls3Instance import (
    EasyControls3Instance,
)

from .conftest import HOST, SERIAL


def _unit(*, reachable: bool = True, serial: int = SERIAL):
    """Patch the connection test to answer as a unit with the given serial."""

    async def test_connection(self: EasyControls3Instance) -> bool:
        self._SerialNR = serial
        return reachable

    return patch.object(EasyControls3Instance, "test_connection", test_connection)


def _add_entry(hass: HomeAssistant, host: str = HOST) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, title=host, unique_id=host, data={"host": host}
    )
    entry.add_to_hass(hass)
    return entry


async def _start(
    hass: HomeAssistant, source: str, entry: MockConfigEntry | None = None
):
    context = {"source": source}
    if entry is not None:
        context["entry_id"] = entry.entry_id
    return await hass.config_entries.flow.async_init(DOMAIN, context=context)


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await _start(hass, SOURCE_USER)
    assert result["type"] is FlowResultType.FORM

    with (
        _unit(),
        patch(
            "custom_components.helios_easycontrols3.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": HOST}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": HOST}
    assert result["result"].unique_id == HOST


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    result = await _start(hass, SOURCE_USER)
    with _unit(reachable=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": HOST}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_duplicate_host(hass: HomeAssistant) -> None:
    _add_entry(hass)
    result = await _start(hass, SOURCE_USER)
    with _unit():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": HOST}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
