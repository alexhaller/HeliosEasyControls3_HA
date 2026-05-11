from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    CONCENTRATION_PARTS_PER_MILLION,
    UnitOfTime,
)
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

    entities: list[EasyControls3BaseEntity] = [
        TemperatureSensor(
            coordinator,
            "OutsideTemperature",
            "Outside Temperature",
            "OutsideTemperature",
        ),
        TemperatureSensor(
            coordinator, "SupplyTemperature", "Supply Temperature", "SupplyTemperature"
        ),
        TemperatureSensor(
            coordinator, "IndoorTemperature", "Indoor Temperature", "IndoorTemperature"
        ),
        TemperatureSensor(
            coordinator,
            "ExhaustTemperature",
            "Exhaust Temperature",
            "ExhaustTemperature",
        ),
        HumiditySensor(coordinator),
        CurrentFanSpeed(coordinator),
        ExtractFanRPMSensor(coordinator),
        SupplyFanRPMSensor(coordinator),
        CellStateSensor(coordinator),
        FilterChanged(coordinator),
        FilterDue(coordinator),
        FilterRemainingDaysSensor(coordinator),
        TotalUptimeYearsSensor(coordinator),
        TotalUptimeHoursSensor(coordinator),
        CurrentUptimeHoursSensor(coordinator),
        HeatRecoveryEfficiency(coordinator),
        ExtraTimerRemainingSensor(coordinator),
        BoostTimerRemainingSensor(coordinator),
        FireplaceTimerRemainingSensor(coordinator),
        TemperatureSensor(
            coordinator,
            "SupplyCellAirTemperature",
            "Supply Cell Air Temperature",
            "SupplyCellAirTemperature",
        ),
    ]

    for i in range(6):
        if coordinator.data.rhSensor(i) is not None:
            entities.append(RHSensor(coordinator, i))
    for i in range(6):
        if coordinator.data.co2Sensor(i) is not None:
            entities.append(CO2Sensor(coordinator, i))
    for i in range(4):
        if coordinator.data.vocSensor(i) is not None:
            entities.append(VOCSensor(coordinator, i))

    async_add_entities(entities)


class TemperatureSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
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

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_AirRH"
        self._attr_name = f"{self._device.deviceModel} Air Relative Humidity"

    @property
    def native_value(self):
        return self._device.AirRH


class RHSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: EasyControls3Coordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"{self._device.serialNR}_rhSensor_{index}"
        self._attr_name = f"{self._device.deviceModel} RH Sensor {index}"

    @property
    def native_value(self):
        return self._device.rhSensor(self._index)

    @property
    def available(self) -> bool:
        return super().available and self._device.rhSensor(self._index) is not None


class CO2Sensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.CO2
    native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"{self._device.serialNR}_co2Sensor_{index}"
        self._attr_name = f"{self._device.deviceModel} CO2 Sensor {index}"

    @property
    def native_value(self):
        return self._device.co2Sensor(self._index)

    @property
    def available(self) -> bool:
        return super().available and self._device.co2Sensor(self._index) is not None


class VOCSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS
    native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"{self._device.serialNR}_vocSensor_{index}"
        self._attr_name = f"{self._device.deviceModel} VOC Sensor {index}"

    @property
    def native_value(self):
        return self._device.vocSensor(self._index)

    @property
    def available(self) -> bool:
        return super().available and self._device.vocSensor(self._index) is not None


class CurrentFanSpeed(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CurrentFanSpeed"
        self._attr_name = f"{self._device.deviceModel} Current Fan Speed"

    @property
    def native_value(self):
        return self._device.CurrentFanSpeed

    @property
    def icon(self) -> str:
        return "mdi:fan"


class ExtractFanRPMSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = "RPM"
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_ExtractFanRPM"
        self._attr_name = f"{self._device.deviceModel} Extract Fan RPM"

    @property
    def native_value(self):
        return self._device.ExtractFanRPM

    @property
    def icon(self) -> str:
        return "mdi:fan"


class SupplyFanRPMSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = "RPM"
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_SupplyFanRPM"
        self._attr_name = f"{self._device.deviceModel} Supply Fan RPM"

    @property
    def native_value(self):
        return self._device.SupplyFanRPM

    @property
    def icon(self) -> str:
        return "mdi:fan"


class CellStateSensor(EasyControls3BaseEntity, SensorEntity):
    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CellState"
        self._attr_name = f"{self._device.deviceModel} Cell State"

    @property
    def native_value(self) -> str | None:
        state = self._device.CellState
        return state.name if state is not None else None

    @property
    def icon(self) -> str:
        return "mdi:heat-wave"


class FilterChanged(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
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

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_filterDue"
        self._attr_name = f"{self._device.deviceModel} Next Filter Change"

    @property
    def native_value(self):
        return self._device.filterDue

    @property
    def icon(self) -> str:
        return "mdi:calendar-alert-outline"


class FilterRemainingDaysSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.DAYS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_FilterRemainingDays"
        self._attr_name = f"{self._device.deviceModel} Filter Remaining Days"

    @property
    def native_value(self):
        return self._device.FilterRemainingDays

    @property
    def icon(self) -> str:
        return "mdi:calendar-clock"


class TotalUptimeYearsSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = UnitOfTime.YEARS
    state_class = SensorStateClass.TOTAL_INCREASING
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_TotalUptimeYears"
        self._attr_name = f"{self._device.deviceModel} Total Uptime Years"

    @property
    def native_value(self):
        return self._device.TotalUptimeYears

    @property
    def icon(self) -> str:
        return "mdi:timer-outline"


class TotalUptimeHoursSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = UnitOfTime.HOURS
    state_class = SensorStateClass.TOTAL_INCREASING
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_TotalUptimeHours"
        self._attr_name = f"{self._device.deviceModel} Total Uptime Hours"

    @property
    def native_value(self):
        return self._device.TotalUptimeHours

    @property
    def icon(self) -> str:
        return "mdi:timer-outline"


class CurrentUptimeHoursSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = UnitOfTime.HOURS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CurrentUptimeHours"
        self._attr_name = f"{self._device.deviceModel} Current Uptime Hours"

    @property
    def native_value(self):
        return self._device.CurrentUptimeHours

    @property
    def icon(self) -> str:
        return "mdi:timer-outline"


class ExtraTimerRemainingSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.MINUTES
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_ExtraTimerRemaining"
        self._attr_name = f"{self._device.deviceModel} Extra Mode Timer Remaining"

    @property
    def native_value(self):
        return self._device.ExtraTimerRemaining

    @property
    def icon(self) -> str:
        return "mdi:timer-outline"


class BoostTimerRemainingSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.MINUTES
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_BoostTimerRemaining"
        self._attr_name = f"{self._device.deviceModel} Intensive Mode Timer Remaining"

    @property
    def native_value(self):
        return self._device.BoostTimerRemaining

    @property
    def icon(self) -> str:
        return "mdi:timer-outline"


class FireplaceTimerRemainingSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.MINUTES
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_FireplaceTimerRemaining"
        self._attr_name = f"{self._device.deviceModel} Fireplace Mode Timer Remaining"

    @property
    def native_value(self):
        return self._device.FireplaceTimerRemaining

    @property
    def icon(self) -> str:
        return "mdi:timer-outline"


class HeatRecoveryEfficiency(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
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
