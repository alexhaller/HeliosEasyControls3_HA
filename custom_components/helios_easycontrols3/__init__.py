"""EasyControls3 Home Assistant integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.loader import IntegrationNotFound, async_get_integration

from .const import DOMAIN, LEGACY_DOMAIN
from .EasyControls3Instance import EasyControls3Instance

type EasyControls3Coordinator = DataUpdateCoordinator[EasyControls3Instance]
type EasyControls3ConfigEntry = ConfigEntry[EasyControls3Coordinator]

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.DATE,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.TIME,
    Platform.SWITCH,
]

SCAN_INTERVAL = timedelta(seconds=60)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import config entries left behind under the pre-2026.11 domain."""
    legacy_entries = hass.config_entries.async_entries(LEGACY_DOMAIN)
    if not legacy_entries:
        return True

    try:
        await async_get_integration(hass, LEGACY_DOMAIN)
    except IntegrationNotFound:
        pass
    else:
        # Both versions installed side by side would drive the same unit, and
        # entities of a loaded integration cannot be moved.
        _LOGGER.error(
            "Remove the old custom_components/%s folder and restart; its "
            "entries are migrated to %s once it is gone",
            LEGACY_DOMAIN,
            DOMAIN,
        )
        return True

    for legacy in legacy_entries:
        # Not awaited: the new entry is set up as soon as it is added, and that
        # setup waits for this component setup to finish.
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={"host": legacy.data["host"], "title": legacy.title},
            )
        )
    return True


async def _async_adopt_legacy_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move the device and entities of the matching legacy entry to this entry.

    Runs before the platforms are set up, so the entities are found under their
    old entity IDs and keep their history, dashboards and automations.
    """
    # Matched on the host: entries created before 2026-05-14 have no unique_id.
    legacy = next(
        (
            candidate
            for candidate in hass.config_entries.async_entries(LEGACY_DOMAIN)
            if candidate.data.get("host") == entry.data["host"]
        ),
        None,
    )
    if legacy is None:
        return

    # Entities first: moving the device off the legacy entry removes every entity
    # on it that still belongs to that entry.
    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, legacy.entry_id):
        entity_registry.async_update_entity_platform(
            entity.entity_id, DOMAIN, new_config_entry_id=entry.entry_id
        )

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, legacy.entry_id):
        device_registry.async_update_device(
            device.id,
            new_config_entry_id=entry.entry_id,
            new_identifiers={
                (DOMAIN if domain == LEGACY_DOMAIN else domain, identifier)
                for domain, identifier in device.identifiers
            },
        )

    await hass.config_entries.async_remove(legacy.entry_id)
    _LOGGER.info("Migrated %s from %s to %s", entry.title, LEGACY_DOMAIN, DOMAIN)


async def async_setup_entry(
    hass: HomeAssistant, entry: EasyControls3ConfigEntry
) -> bool:
    await _async_adopt_legacy_entry(hass, entry)
    device = EasyControls3Instance(entry.data["host"])

    async def _async_update_data() -> EasyControls3Instance:
        try:
            await device.readCurrentData()
        except Exception as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        return device

    coordinator: EasyControls3Coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_method=_async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EasyControls3ConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class EasyControls3BaseEntity(CoordinatorEntity[EasyControls3Coordinator]):
    """Base entity for all EasyControls3 entities."""

    has_entity_name = True

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._device: EasyControls3Instance = coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device.serialNR))},
            name=self._device.deviceModel,
            manufacturer="Helios",
            model=self._device.deviceType,
            sw_version=self._device.firmwareVersion,
        )
