from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        DefrostingBinarySensor(coordinator),
        EmergencyStopBinarySensor(coordinator),
        BypassBinarySensor(coordinator),
        WeeklyTimerBinarySensor(coordinator),
    ])


class DefrostingBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.COLD

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_Defrosting"
        self._attr_name = f"{self._device.deviceModel} Defrosting"

    @property
    def is_on(self) -> bool | None:
        return self._device.Defrosting

    @property
    def icon(self) -> str:
        return "mdi:snowflake"


class EmergencyStopBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_EmergencyStop"
        self._attr_name = f"{self._device.deviceModel} Emergency Stop"

    @property
    def is_on(self) -> bool | None:
        return self._device.EmergencyStopActivated


class BypassBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_BypassOpen"
        self._attr_name = f"{self._device.deviceModel} Bypass Open"

    @property
    def is_on(self) -> bool | None:
        return self._device.BypassOpen

    @property
    def icon(self) -> str:
        return "mdi:valve-open"


class WeeklyTimerBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_WeeklyTimerEnabled"
        self._attr_name = f"{self._device.deviceModel} Weekly Timer Enabled"

    @property
    def is_on(self) -> bool | None:
        return self._device.WeeklyTimerEnabled

    @property
    def icon(self) -> str:
        return "mdi:calendar-clock"
