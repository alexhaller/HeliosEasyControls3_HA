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
        TemperatureSensor(coordinator, "OutsideTemperature", "Outside Temperature", "OutsideTemperature"),
        TemperatureSensor(coordinator, "SupplyTemperature", "Supply Temperature", "SupplyTemperature"),
        TemperatureSensor(coordinator, "IndoorTemperature", "Indoor Temperature", "IndoorTemperature"),
        TemperatureSensor(coordinator, "ExhaustTemperature", "Exhaust Temperature", "ExhaustTemperature"),
        HumiditySensor(coordinator),
        CurrentFanSpeed(coordinator),
        FilterChanged(coordinator),
        FilterDue(coordinator),
        HeatRecoveryEfficiency(coordinator),
    ]

    if coordinator.data.CO2Value != 0xFFFF:  # only add CO2 sensor if it is available
        entities.append(CO2Sensor(coordinator))

    async_add_entities(entities)


class TemperatureSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        unique_suffix: str,
        name_suffix: str,
        device_attr: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = f"{self._device.deviceModel} {name_suffix}"
        self._device_attr = device_attr

    @property
    def native_value(self):
        return getattr(self._device, self._device_attr)


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


class HeatRecoveryEfficiency(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_HeatRecoveryEfficiency"
        self._attr_name = f"{self._device.deviceModel} Heat Recovery Efficiency"

    @property
    def native_value(self):
        supply = self._device.SupplyTemperature
        outside = self._device.OutsideTemperature
        indoor = self._device.IndoorTemperature
        denominator = indoor - outside
        if denominator == 0:
            return None
        return round((supply - outside) / denominator * 100, 1)

    @property
    def icon(self) -> str:
        return "mdi:heat-wave"
