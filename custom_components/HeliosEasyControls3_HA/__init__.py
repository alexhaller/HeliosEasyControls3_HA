"""EasyControls3 Home Assistant integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance

EasyControls3Coordinator = DataUpdateCoordinator[EasyControls3Instance]

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.TIME, Platform.SWITCH]

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    device = EasyControls3Instance(entry.data["host"])

    async def _async_update_data():
        try:
            await device.readCurrentData()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
        return device

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class EasyControls3BaseEntity(CoordinatorEntity[EasyControls3Coordinator]):
    """Base entity for all EasyControls3 entities."""

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
        )
