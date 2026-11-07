"""Migration of entries left under the pre-v3 domain HeliosEasyControls3_HA."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.helios_easycontrols3.const import DOMAIN, LEGACY_DOMAIN

from .conftest import HOST, SERIAL

ENTITY_ID = "sensor.helios_outside_temperature"


def _add_legacy_install(hass: HomeAssistant) -> MockConfigEntry:
    """Register an entry, device and entity the way v2 left them behind."""
    legacy = MockConfigEntry(
        domain=LEGACY_DOMAIN,
        title="Helios Keller",
        unique_id=HOST,
        data={"host": HOST},
    )
    legacy.add_to_hass(hass)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=legacy.entry_id,
        identifiers={(LEGACY_DOMAIN, str(SERIAL))},
        name="KWL 360 W ET",
    )
    er.async_get(hass).async_get_or_create(
        "sensor",
        LEGACY_DOMAIN,
        f"{SERIAL}_OutsideTemperature",
        config_entry=legacy,
        device_id=device.id,
        suggested_object_id="helios_outside_temperature",
    )
    return legacy


@pytest.mark.usefixtures("mock_unit")
async def test_legacy_entry_is_migrated(hass: HomeAssistant) -> None:
    """Entry, device and entity move over and keep their entity ID."""
    legacy = _add_legacy_install(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert hass.config_entries.async_get_entry(legacy.entry_id) is None
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.unique_id == HOST
    assert entry.title == "Helios Keller"
    assert entry.data == {"host": HOST}
    assert entry.state is ConfigEntryState.LOADED

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, str(SERIAL)), entry.entry_id
    )
    assert device is not None
    assert device.config_entry_id == entry.entry_id
    assert device.identifiers == {(DOMAIN, str(SERIAL))}

    entity = er.async_get(hass).async_get(ENTITY_ID)
    assert entity is not None
    assert entity.platform == DOMAIN
    assert entity.config_entry_id == entry.entry_id
    assert entity.device_id == device.id
    # Loaded under its old entity ID, not as a fresh sensor.*_2 next to it
    assert hass.states.get(ENTITY_ID) is not None
    assert hass.states.get(f"{ENTITY_ID}_2") is None


@pytest.mark.usefixtures("mock_unit")
async def test_nothing_to_migrate(hass: HomeAssistant) -> None:
    """A fresh install sets up without creating any entry."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == []


@pytest.mark.usefixtures("mock_unit")
async def test_legacy_integration_still_installed(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """With the old folder still present nothing is touched."""
    legacy = _add_legacy_install(hass)

    with patch(
        "custom_components.helios_easycontrols3.async_get_integration",
        AsyncMock(),
    ):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    assert hass.config_entries.async_get_entry(legacy.entry_id) is legacy
    assert hass.config_entries.async_entries(DOMAIN) == []
    assert er.async_get(hass).async_get(ENTITY_ID).platform == LEGACY_DOMAIN
    assert "Remove the old custom_components/HeliosEasyControls3_HA" in caplog.text


@pytest.mark.usefixtures("mock_unit")
async def test_import_skips_configured_host(hass: HomeAssistant) -> None:
    """An entry re-added by hand under the new domain still adopts the legacy one."""
    legacy = _add_legacy_install(hass)
    existing = MockConfigEntry(
        domain=DOMAIN, title=HOST, unique_id=HOST, data={"host": HOST}
    )
    existing.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == [existing]
    assert hass.config_entries.async_get_entry(legacy.entry_id) is None
    entity = er.async_get(hass).async_get(ENTITY_ID)
    assert entity.config_entry_id == existing.entry_id
