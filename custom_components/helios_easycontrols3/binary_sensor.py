from collections.abc import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance

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
            StateBinarySensor(
                coordinator,
                "ioError",
                "Error Output",
                lambda d: d.IoError,
                device_class=BinarySensorDeviceClass.PROBLEM,
            ),
            StateBinarySensor(
                coordinator,
                "ioHeater",
                "Heater Active",
                lambda d: d.IoHeater,
                icon="mdi:radiator",
            ),
            StateBinarySensor(
                coordinator,
                "ioExtraHeater",
                "Extra Heater Active",
                lambda d: d.IoExtraHeater,
                icon="mdi:radiator",
            ),
            StateBinarySensor(
                coordinator,
                "limpMode",
                "Limp Mode",
                lambda d: d.LimpMode,
                device_class=BinarySensorDeviceClass.PROBLEM,
                diagnostic=True,
            ),
            StateBinarySensor(
                coordinator,
                "constantAirflowAlert",
                "Constant Airflow Alert",
                lambda d: d.ConstantAirflowAlert,
                device_class=BinarySensorDeviceClass.PROBLEM,
                diagnostic=True,
            ),
            StateBinarySensor(
                coordinator,
                "deviceEnabled",
                "Device Enabled",
                lambda d: d.DeviceEnabled,
                diagnostic=True,
            ),
            StateBinarySensor(
                coordinator,
                "cfLimiterActive",
                "Constant Flow Limiter Active",
                lambda d: d.CfLimiterActive,
                diagnostic=True,
            ),
            StateBinarySensor(
                coordinator,
                "torConnected",
                "Post Heater Module Connected",
                lambda d: d.TorConnected,
                diagnostic=True,
            ),
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


class StateBinarySensor(EasyControls3BaseEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], bool | None],
        device_class: BinarySensorDeviceClass | None = None,
        icon: str | None = None,
        diagnostic: bool = False,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        if device_class is not None:
            self._attr_device_class = device_class
        if icon is not None:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False

    @property
    def is_on(self) -> bool | None:
        return self._getter(self._device)
