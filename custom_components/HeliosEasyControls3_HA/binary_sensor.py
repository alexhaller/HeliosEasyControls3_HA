from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            DefrostingBinarySensor(coordinator),
            EmergencyStopBinarySensor(coordinator),
            BypassBinarySensor(coordinator),
        ]
    )


class DefrostingBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.COLD
    _attr_icon = "mdi:snowflake"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_Defrosting"
        self._attr_name = "Defrosting"

    @property
    def is_on(self) -> bool | None:
        return self._device.Defrosting


class EmergencyStopBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_EmergencyStop"
        self._attr_name = "Emergency Stop"

    @property
    def is_on(self) -> bool | None:
        return self._device.EmergencyStopActivated


class BypassBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:valve-open"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_BypassOpen"
        self._attr_name = "Bypass Status"

    @property
    def is_on(self) -> bool | None:
        return self._device.BypassOpen
