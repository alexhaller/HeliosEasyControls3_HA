from collections.abc import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
)
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

    entities: list[EasyControls3BaseEntity] = [
        TemperatureSensor(
            coordinator,
            "OutsideTemperature",
            "Outside Temperature",
            lambda d: d.OutsideTemperature,
        ),
        TemperatureSensor(
            coordinator,
            "SupplyTemperature",
            "Supply Temperature",
            lambda d: d.SupplyTemperature,
        ),
        TemperatureSensor(
            coordinator,
            "IndoorTemperature",
            "Indoor Temperature",
            lambda d: d.IndoorTemperature,
        ),
        TemperatureSensor(
            coordinator,
            "ExhaustTemperature",
            "Exhaust Temperature",
            lambda d: d.ExhaustTemperature,
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
        RHSensorCountSensor(coordinator),
        CO2SensorCountSensor(coordinator),
        VOCSensorCountSensor(coordinator),
        HeatRecoveryEfficiency(coordinator),
        ExtraTimerRemainingSensor(coordinator),
        BoostTimerRemainingSensor(coordinator),
        IndividualTimerRemainingSensor(coordinator),
    ]

    if coordinator.data.multisensorTemp is not None:
        entities.append(
            TemperatureSensor(
                coordinator,
                "multisensorTemp",
                "Multisensor Temperature",
                lambda d: d.multisensorTemp,
            )
        )
    if coordinator.data.multisensorRH is not None:
        entities.append(MultisensorHumiditySensor(coordinator))
    if coordinator.data.co2Value is not None:
        entities.append(CO2ValueSensor(coordinator))

    entities += [
        DiagnosticSensor(
            coordinator,
            "ioExtractFan",
            "Extract Fan Output",
            lambda d: d.IoExtractFan,
            icon="mdi:fan",
        ),
        DiagnosticSensor(
            coordinator,
            "ioSupplyFan",
            "Supply Fan Output",
            lambda d: d.IoSupplyFan,
            icon="mdi:fan",
        ),
        DiagnosticSensor(coordinator, "rhLevel", "RH Level", lambda d: d.rhLevel),
        DiagnosticSensor(coordinator, "co2Level", "CO2 Level", lambda d: d.co2Level),
        DiagnosticSensor(coordinator, "mlvState", "MLV State", lambda d: d.MlvState),
        DiagnosticSensor(
            coordinator, "cloudStatus", "Cloud Status", lambda d: d.CloudStatus
        ),
        DiagnosticSensor(
            coordinator,
            "measuredSupply",
            "Measured Supply Airflow",
            lambda d: d.MeasuredSupply,
        ),
        DiagnosticSensor(
            coordinator,
            "measuredExtract",
            "Measured Extract Airflow",
            lambda d: d.MeasuredExtract,
        ),
        DiagnosticSensor(
            coordinator,
            "cfSupplyFanLoad",
            "Constant Flow Supply Fan Load",
            lambda d: d.cfSupplyFanLoad,
        ),
        DiagnosticSensor(
            coordinator,
            "cfExtractFanLoad",
            "Constant Flow Extract Fan Load",
            lambda d: d.cfExtractFanLoad,
        ),
        DiagnosticSensor(
            coordinator, "supplyAirflow", "Supply Airflow", lambda d: d.SupplyAirflow
        ),
        DiagnosticSensor(
            coordinator, "extractAirflow", "Extract Airflow", lambda d: d.ExtractAirflow
        ),
        DiagnosticSensor(
            coordinator,
            "condensationPrevention",
            "Condensation Prevention",
            lambda d: d.condensationPrevention,
        ),
        DiagnosticSensor(
            coordinator,
            "constantFanMax",
            "Constant Fan Max Value",
            lambda d: d.constantFanMax,
        ),
        DiagnosticSensor(
            coordinator,
            "constantFanMin",
            "Constant Fan Min Value",
            lambda d: d.constantFanMin,
        ),
        DiagnosticSensor(
            coordinator,
            "constantFanBalance",
            "Constant Fan Balance",
            lambda d: d.constantFanBalance,
        ),
        DiagnosticSensor(
            coordinator,
            "timedFunctionReturnMode",
            "Timed Function Return Mode",
            lambda d: d.timedFunctionReturnMode,
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
        name: str,
        getter: Callable[[EasyControls3Instance], float | None],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter

    @property
    def native_value(self) -> float | None:
        return self._getter(self._device)


class HumiditySensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_AirRH"
        self._attr_name = "Air Relative Humidity"

    @property
    def native_value(self) -> int | None:
        return self._device.AirRH


class MultisensorHumiditySensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_multisensorRH"
        self._attr_name = "Multisensor Humidity"

    @property
    def native_value(self) -> int | None:
        return self._device.multisensorRH


class CO2ValueSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.CO2
    native_unit_of_measurement = UnitOfRatio.PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_co2Value"
        self._attr_name = "CO2 Value"

    @property
    def native_value(self) -> int | None:
        return self._device.co2Value

    @property
    def available(self) -> bool:
        return super().available and self._device.co2Value is not None


class DiagnosticSensor(EasyControls3BaseEntity, SensorEntity):
    """Raw register value, off by default: useful for support, not for daily use."""

    entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], int | None],
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        if icon is not None:
            self._attr_icon = icon

    @property
    def native_value(self) -> int | None:
        return self._getter(self._device)


class RHSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.HUMIDITY
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, coordinator: EasyControls3Coordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"{self._device.serialNR}_rhSensor_{index}"
        self._attr_name = f"RH Sensor {index}"

    @property
    def native_value(self) -> int | None:
        return self._device.rhSensor(self._index)

    @property
    def available(self) -> bool:
        return super().available and self._device.rhSensor(self._index) is not None


class CO2Sensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.CO2
    native_unit_of_measurement = UnitOfRatio.PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"{self._device.serialNR}_co2Sensor_{index}"
        self._attr_name = f"CO2 Sensor {index}"

    @property
    def native_value(self) -> int | None:
        return self._device.co2Sensor(self._index)

    @property
    def available(self) -> bool:
        return super().available and self._device.co2Sensor(self._index) is not None


class VOCSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS
    native_unit_of_measurement = UnitOfRatio.PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0

    def __init__(self, coordinator: EasyControls3Coordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_unique_id = f"{self._device.serialNR}_vocSensor_{index}"
        self._attr_name = f"VOC Sensor {index}"

    @property
    def native_value(self) -> int | None:
        return self._device.vocSensor(self._index)

    @property
    def available(self) -> bool:
        return super().available and self._device.vocSensor(self._index) is not None


class CurrentFanSpeed(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CurrentFanSpeed"
        self._attr_name = "Current Fan Speed"

    @property
    def native_value(self) -> int | None:
        return self._device.CurrentFanSpeed


class ExtractFanRPMSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = "RPM"
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_ExtractFanRPM"
        self._attr_name = "Extract Fan RPM"

    @property
    def native_value(self) -> int | None:
        return self._device.ExtractFanRPM


class SupplyFanRPMSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = "RPM"
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_SupplyFanRPM"
        self._attr_name = "Supply Fan RPM"

    @property
    def native_value(self) -> int | None:
        return self._device.SupplyFanRPM


class CellStateSensor(EasyControls3BaseEntity, SensorEntity):
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CellState"
        self._attr_name = "Cell State"

    @property
    def native_value(self) -> str | None:
        state = self._device.CellState
        return state.name if state is not None else None


class FilterChanged(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DATE
    entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-sync-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_filterChanged"
        self._attr_name = "Last Filter Change"

    @property
    def native_value(self):
        return self._device.filterChanged


class FilterDue(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DATE
    entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-alert-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_filterDue"
        self._attr_name = "Next Filter Change"

    @property
    def native_value(self):
        return self._device.filterDue


class FilterRemainingDaysSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.DAYS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_FilterRemainingDays"
        self._attr_name = "Filter Remaining Days"

    @property
    def native_value(self) -> int | None:
        return self._device.FilterRemainingDays


class TotalUptimeYearsSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = UnitOfTime.YEARS
    state_class = SensorStateClass.TOTAL_INCREASING
    suggested_display_precision = 0
    entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_TotalUptimeYears"
        self._attr_name = "Total Uptime Years"

    @property
    def native_value(self) -> int | None:
        return self._device.TotalUptimeYears


class TotalUptimeHoursSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = UnitOfTime.HOURS
    state_class = SensorStateClass.TOTAL_INCREASING
    suggested_display_precision = 0
    entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_TotalUptimeHours"
        self._attr_name = "Total Uptime Hours"

    @property
    def native_value(self) -> int | None:
        return self._device.TotalUptimeHours


class CurrentUptimeHoursSensor(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = UnitOfTime.HOURS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CurrentUptimeHours"
        self._attr_name = "Current Uptime Hours"

    @property
    def native_value(self) -> int | None:
        return self._device.CurrentUptimeHours


class ExtraTimerRemainingSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.MINUTES
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_ExtraTimerRemaining"
        self._attr_name = "Extra Mode Timer Remaining"

    @property
    def native_value(self) -> int | None:
        return self._device.ExtraTimerRemaining


class BoostTimerRemainingSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.MINUTES
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_BoostTimerRemaining"
        self._attr_name = "Intensive Mode Timer Remaining"

    @property
    def native_value(self) -> int | None:
        return self._device.BoostTimerRemaining


class IndividualTimerRemainingSensor(EasyControls3BaseEntity, SensorEntity):
    device_class = SensorDeviceClass.DURATION
    native_unit_of_measurement = UnitOfTime.MINUTES
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 0
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_IndividualTimerRemaining"
        self._attr_name = "Individual Mode Timer Remaining"

    @property
    def native_value(self) -> int | None:
        return self._device.IndividualTimerRemaining


class HeatRecoveryEfficiency(EasyControls3BaseEntity, SensorEntity):
    native_unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_HeatRecoveryEfficiency"
        self._attr_name = "Heat Recovery Efficiency"

    @property
    def native_value(self) -> float | None:
        supply = self._device.SupplyTemperature
        outside = self._device.OutsideTemperature
        indoor = self._device.IndoorTemperature
        if supply is None or outside is None or indoor is None:
            return None
        denominator = indoor - outside
        if denominator == 0:
            return None
        return round((supply - outside) / denominator * 100, 1)


class RHSensorCountSensor(EasyControls3BaseEntity, SensorEntity):
    state_class = SensorStateClass.MEASUREMENT
    entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_RHSensorCount"
        self._attr_name = "External RH Sensor Count"

    @property
    def native_value(self) -> int:
        return self._device.rhSensorCount


class CO2SensorCountSensor(EasyControls3BaseEntity, SensorEntity):
    state_class = SensorStateClass.MEASUREMENT
    entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_CO2SensorCount"
        self._attr_name = "CO2 Sensor Count"

    @property
    def native_value(self) -> int:
        return self._device.co2SensorCount


class VOCSensorCountSensor(EasyControls3BaseEntity, SensorEntity):
    state_class = SensorStateClass.MEASUREMENT
    entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_VOCSensorCount"
        self._attr_name = "VOC Sensor Count"

    @property
    def native_value(self) -> int:
        return self._device.vocSensorCount
