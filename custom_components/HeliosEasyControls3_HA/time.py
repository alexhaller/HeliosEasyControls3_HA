from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import EasyControls3BaseEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([IntensiveDuration(coordinator)])


class IntensiveDuration(EasyControls3BaseEntity, TimeEntity):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_intensiveDuration"
        self._attr_name = f"{self._device.deviceModel} Intensive Mode Duration"

    @property
    def native_value(self) -> time:
        return self._device.IntensivDuration

    async def async_set_value(self, value: time) -> None:
        await self._device.setIntensiveDuration(value)
        await self.coordinator.async_request_refresh()
