from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    CONCENTRATION_PARTS_PER_MILLION,
)
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

    entities = [
        HumiditySensor(coordinator),
        OutsideTemperatureSensor(coordinator),
        SupplyTemperatureSensor(coordinator),
        IndoorTemperatureSensor(coordinator),
        ExhaustTemperatureSensor(coordinator),
        CurrentFanSpeed(coordinator),
        FilterChanged(coordinator),
        FilterDue(coordinator),
    ]

    if coordinator.data.CO2Value != 0xFFFF:  # only add CO2 sensor if it is available
        entities.append(CO2Sensor(coordinator))

    async_add_entities(entities)


class HumiditySensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_AirRH"
        self._attr_name = f"{self._device.deviceModel} Air Relative Humidity"

    @property
    def native_value(self):
        return self._device.AirRH


class OutsideTemperatureSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_OutsideTemperature"
        self._attr_name = f"{self._device.deviceModel} Outside Temperature"

    @property
    def native_value(self):
        return self._device.OutsideTemperature


class SupplyTemperatureSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_SupplyTemperature"
        self._attr_name = f"{self._device.deviceModel} Supply Temperature"

    @property
    def native_value(self):
        return self._device.SupplyTemperature


class IndoorTemperatureSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_IndoorTemperature"
        self._attr_name = f"{self._device.deviceModel} Indoor Temperature"

    @property
    def native_value(self):
        return self._device.IndoorTemperature


class ExhaustTemperatureSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_ExhaustTemperature"
        self._attr_name = f"{self._device.deviceModel} Exhaust Temperature"

    @property
    def native_value(self):
        return self._device.ExhaustTemperature


class CO2Sensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.CO2
    native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CO2Value"
        self._attr_name = f"{self._device.deviceModel} CO2 Value"

    @property
    def native_value(self):
        return self._device.CO2Value

    @property
    def available(self) -> bool:
        return super().available and self._device.CO2Value != 0xFFFF


class CurrentFanSpeed(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CurrentFanSpeed"
        self._attr_name = f"{self._device.deviceModel} Current Fan Speed"

    @property
    def native_value(self):
        return self._device.CurrentFanSpeed

    @property
    def icon(self) -> str:
        return "mdi:fan"


class FilterChanged(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_filterChanged"
        self._attr_name = f"{self._device.deviceModel} Last Filter Change"

    @property
    def native_value(self):
        return self._device.filterChanged

    @property
    def icon(self) -> str:
        return "mdi:calendar-sync-outline"


class FilterDue(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_filterDue"
        self._attr_name = f"{self._device.deviceModel} Next Filter Change"

    @property
    def native_value(self):
        return self._device.filterDue

    @property
    def icon(self) -> str:
        return "mdi:calendar-alert-outline"
