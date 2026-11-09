"""Config flow: initial setup and reconfiguring the host of an entry."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant.common import MockConfigEntry

from custom_components.helios_easycontrols3.const import DOMAIN
from custom_components.helios_easycontrols3.EasyControls3Instance import (
    EasyControls3Instance,
)

from .conftest import HOST, SERIAL

NEW_HOST = "192.168.1.200"


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


def _add_device(hass: HomeAssistant, entry: MockConfigEntry, serial: int) -> None:
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, str(serial))}
    )


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


async def test_reconfigure_updates_host(hass: HomeAssistant) -> None:
    entry = _add_entry(hass)
    _add_device(hass, entry, SERIAL)
    result = await _start(hass, "reconfigure", entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        _unit(),
        patch(
            "custom_components.helios_easycontrols3.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": NEW_HOST}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {"host": NEW_HOST}
    assert entry.unique_id == NEW_HOST
    assert entry.title == NEW_HOST
    # The device stays where it is, so its entities keep their IDs
    assert (
        dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, str(SERIAL)), entry.entry_id
        )
        is not None
    )


async def test_reconfigure_keeps_custom_title(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, title="Keller", unique_id=HOST, data={"host": HOST}
    )
    entry.add_to_hass(hass)
    result = await _start(hass, "reconfigure", entry)
    with (
        _unit(),
        patch(
            "custom_components.helios_easycontrols3.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": NEW_HOST}
        )

    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == NEW_HOST
    assert entry.title == "Keller"
    assert entry.data == {"host": NEW_HOST}


async def test_reconfigure_entry_without_device(hass: HomeAssistant) -> None:
    """Nothing to compare the serial with yet: the new host is accepted."""
    entry = _add_entry(hass)
    result = await _start(hass, "reconfigure", entry)
    with (
        _unit(serial=SERIAL + 1),
        patch(
            "custom_components.helios_easycontrols3.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": NEW_HOST}
        )

    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {"host": NEW_HOST}


async def test_reconfigure_same_host(hass: HomeAssistant) -> None:
    """Re-submitting the current host is not a duplicate of itself."""
    entry = _add_entry(hass)
    _add_device(hass, entry, SERIAL)
    result = await _start(hass, "reconfigure", entry)
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

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {"host": HOST}


async def test_reconfigure_cannot_connect(hass: HomeAssistant) -> None:
    entry = _add_entry(hass)
    result = await _start(hass, "reconfigure", entry)
    with _unit(reachable=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": NEW_HOST}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data == {"host": HOST}


@pytest.mark.parametrize("host", ["not a host!", "-bad"])
async def test_reconfigure_invalid_host(hass: HomeAssistant, host: str) -> None:
    entry = _add_entry(hass)
    result = await _start(hass, "reconfigure", entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": host}
    )

    assert result["errors"] == {"host": "invalid_host"}
    assert entry.data == {"host": HOST}


async def test_reconfigure_host_of_other_entry(hass: HomeAssistant) -> None:
    entry = _add_entry(hass)
    _add_entry(hass, NEW_HOST)
    result = await _start(hass, "reconfigure", entry)
    with _unit():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": NEW_HOST}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data == {"host": HOST}


async def test_reconfigure_different_unit_rejected(hass: HomeAssistant) -> None:
    entry = _add_entry(hass)
    _add_device(hass, entry, SERIAL)
    result = await _start(hass, "reconfigure", entry)
    with _unit(serial=SERIAL + 1):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": NEW_HOST}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wrong_device"}
    assert entry.data == {"host": HOST}
