from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import EasyControls3BaseEntity
from .const import DOMAIN
from .KWLStates import KWLState


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            FanSpeedNumberAtHome(coordinator),
            FanSpeedNumberAway(coordinator),
            FanSpeedNumberIntensive(coordinator),
        ]
    )


class FanSpeedNumber(EasyControls3BaseEntity, NumberEntity):
    """Base fan speed number entity."""

    native_min_value = 1.0
    native_max_value = 100.0
    native_step = 1.0

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def icon(self) -> str:
        return "mdi:fan"


class FanSpeedNumberAtHome(FanSpeedNumber):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_atHomeFanSpeed"
        self._attr_name = f"{self._device.deviceModel} Fan Speed At Home"

    @property
    def native_value(self):
        return self._device.AtHomeFanSpeed

    async def async_set_native_value(self, value: float) -> None:
        await self._device.setAtHomeFanSpeed(value)
        await self.coordinator.async_request_refresh()


class FanSpeedNumberAway(FanSpeedNumber):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_awayFanSpeed"
        self._attr_name = f"{self._device.deviceModel} Fan Speed Away"

    @property
    def native_value(self):
        return self._device.AwayFanSpeed

    async def async_set_native_value(self, value: float) -> None:
        await self._device.setAwayFanSpeed(value)
        await self.coordinator.async_request_refresh()


class FanSpeedNumberIntensive(FanSpeedNumber):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_intensivFanSpeed"
        self._attr_name = f"{self._device.deviceModel} Fan Speed Intensive"

    @property
    def native_value(self):
        return self._device.IntensivFanSpeed

    async def async_set_native_value(self, value: float) -> None:
        await self._device.setIntensiveFanSpeed(value)
        await self.coordinator.async_request_refresh()
