from collections.abc import Awaitable, Callable

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfRatio, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance
from .KWLStates import KWLState

PARALLEL_UPDATES = 1


def _cf_airflow_getter(key: str) -> Callable[[EasyControls3Instance], float | None]:
    def getter(device: EasyControls3Instance) -> float | None:
        return device.cfBaseAirflow(key)

    return getter


def _cf_airflow_setter(
    key: str,
) -> Callable[[EasyControls3Instance, float], Awaitable[None]]:
    def setter(device: EasyControls3Instance, value: float) -> Awaitable[None]:
        return device.setCfBaseAirflow(key, int(value))

    return setter


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            FanSpeedNumber(
                coordinator,
                "atHomeFanSpeed",
                "Fan Speed At Home",
                lambda d: d.AtHomeFanSpeed,
                lambda d, v: d.setFanSpeed(v, KWLState.AtHome),
            ),
            FanSpeedNumber(
                coordinator,
                "awayFanSpeed",
                "Fan Speed Away",
                lambda d: d.AwayFanSpeed,
                lambda d, v: d.setFanSpeed(v, KWLState.Away),
            ),
            FanSpeedNumber(
                coordinator,
                "intensivFanSpeed",
                "Fan Speed Intensive",
                lambda d: d.IntensivFanSpeed,
                lambda d, v: d.setFanSpeed(v, KWLState.Intensive),
            ),
            FanSpeedNumber(
                coordinator,
                "individualExtractFanSpeed",
                "Individual Extract Fan Speed",
                lambda d: d.IndividualExtractFanSpeed,
                lambda d, v: d.setIndividualExtractFanSpeed(v),
            ),
            FanSpeedNumber(
                coordinator,
                "individualSupplyFanSpeed",
                "Individual Supply Fan Speed",
                lambda d: d.IndividualSupplyFanSpeed,
                lambda d, v: d.setIndividualSupplyFanSpeed(v),
            ),
            FanSpeedNumber(
                coordinator,
                "extraExtractFanSpeed",
                "Extra Extract Fan Speed",
                lambda d: d.ExtraExtractFanSpeed,
                lambda d, v: d.setExtraExtractFanSpeed(v),
            ),
            FanSpeedNumber(
                coordinator,
                "extraSupplyFanSpeed",
                "Extra Supply Fan Speed",
                lambda d: d.ExtraSupplyFanSpeed,
                lambda d, v: d.setExtraSupplyFanSpeed(v),
            ),
            AirTempTargetNumber(
                coordinator,
                "homeAirTempTarget",
                "Home Air Temp Target",
                lambda d: d.HomeAirTempTarget,
                lambda d, v: d.setHomeAirTempTarget(v),
            ),
            AirTempTargetNumber(
                coordinator,
                "awayAirTempTarget",
                "Away Air Temp Target",
                lambda d: d.AwayAirTempTarget,
                lambda d, v: d.setAwayAirTempTarget(v),
            ),
            AirTempTargetNumber(
                coordinator,
                "boostAirTempTarget",
                "Intensive Air Temp Target",
                lambda d: d.BoostAirTempTarget,
                lambda d, v: d.setBoostAirTempTarget(v),
            ),
            AirTempTargetNumber(
                coordinator,
                "extraAirTempTarget",
                "Extra Air Temp Target",
                lambda d: d.ExtraAirTempTarget,
                lambda d, v: d.setExtraAirTempTarget(v),
            ),
            AirTempTargetNumber(
                coordinator,
                "individualAirTempTarget",
                "Individual Air Temp Target",
                lambda d: d.IndividualAirTempTarget,
                lambda d, v: d.setIndividualAirTempTarget(v),
            ),
            RHLimitNumber(coordinator),
            CO2LimitNumber(coordinator),
            SettingNumber(
                coordinator,
                "extractFanBalance",
                "Extract Fan Balance",
                lambda d: d.extractFanBalance,
                lambda d, v: d.setExtractFanBalance(int(v)),
                0.0,
                100.0,
                unit=PERCENTAGE,
                icon="mdi:scale-balance",
            ),
            SettingNumber(
                coordinator,
                "supplyFanBalance",
                "Supply Fan Balance",
                lambda d: d.supplyFanBalance,
                lambda d, v: d.setSupplyFanBalance(int(v)),
                0.0,
                100.0,
                unit=PERCENTAGE,
                icon="mdi:scale-balance",
            ),
            SettingNumber(
                coordinator,
                "maxFanSpeedExtract",
                "Max Extract Fan Speed",
                lambda d: d.maxFanSpeedExtract,
                lambda d, v: d.setMaxFanSpeedExtract(int(v)),
                1.0,
                100.0,
                unit=PERCENTAGE,
                icon="mdi:fan-speed-3",
            ),
            SettingNumber(
                coordinator,
                "maxFanSpeedSupply",
                "Max Supply Fan Speed",
                lambda d: d.maxFanSpeedSupply,
                lambda d, v: d.setMaxFanSpeedSupply(int(v)),
                1.0,
                100.0,
                unit=PERCENTAGE,
                icon="mdi:fan-speed-3",
            ),
            SettingNumber(
                coordinator,
                "postHeaterWinterSetpoint",
                "Post Heater Winter Setpoint",
                lambda d: d.postHeaterWinterSetpoint,
                lambda d, v: d.setPostHeaterWinterSetpoint(v),
                0.0,
                19.0,
                unit=UnitOfTemperature.CELSIUS,
                device_class=NumberDeviceClass.TEMPERATURE,
            ),
            SettingNumber(
                coordinator,
                "mlvSupplyLowerLimit",
                "MLV Supply Lower Limit",
                lambda d: d.mlvSupplyLowerLimit,
                lambda d, v: d.setMlvSupplyLowerLimit(v),
                12.0,
                25.0,
                unit=UnitOfTemperature.CELSIUS,
                device_class=NumberDeviceClass.TEMPERATURE,
                diagnostic=True,
            ),
            SettingNumber(
                coordinator,
                "supplyAirDefrostTemp",
                "Supply Air Defrost Temperature",
                lambda d: d.supplyAirDefrostTemp,
                lambda d, v: d.setSupplyAirDefrostTemp(v),
                12.0,
                20.0,
                unit=UnitOfTemperature.CELSIUS,
                device_class=NumberDeviceClass.TEMPERATURE,
                diagnostic=True,
            ),
            SettingNumber(
                coordinator,
                "mlvSummerSetpoint",
                "MLV Summer Setpoint",
                lambda d: d.mlvSummerSetpoint,
                lambda d, v: d.setMlvSummerSetpoint(v),
                12.0,
                25.0,
                unit=UnitOfTemperature.CELSIUS,
                device_class=NumberDeviceClass.TEMPERATURE,
                diagnostic=True,
            ),
            SettingNumber(
                coordinator,
                "mlvWinterSetpoint",
                "MLV Winter Setpoint",
                lambda d: d.mlvWinterSetpoint,
                lambda d, v: d.setMlvWinterSetpoint(v),
                -10.0,
                5.0,
                unit=UnitOfTemperature.CELSIUS,
                device_class=NumberDeviceClass.TEMPERATURE,
                diagnostic=True,
            ),
            SettingNumber(
                coordinator,
                "filterReminderAutoTime",
                "Filter Reminder Automatic Interval",
                lambda d: d.filterReminderAutoTime,
                lambda d, v: d.setFilterReminderAutoTime(int(v)),
                1.0,
                365.0,
                icon="mdi:bell-cog-outline",
                diagnostic=True,
            ),
            *(
                SettingNumber(
                    coordinator,
                    f"cfBaseAirflow_{key}",
                    f"Base Airflow {label}",
                    _cf_airflow_getter(key),
                    _cf_airflow_setter(key),
                    0.0,
                    300.0,
                    icon="mdi:air-filter",
                    diagnostic=True,
                )
                for key, label in (
                    ("away_supply", "Away Supply"),
                    ("away_extract", "Away Extract"),
                    ("home_supply", "Home Supply"),
                    ("home_extract", "Home Extract"),
                    ("boost_supply", "Intensive Supply"),
                    ("boost_extract", "Intensive Extract"),
                )
            ),
        ]
    )


class FanSpeedNumber(EasyControls3BaseEntity, NumberEntity):
    native_min_value = 1.0
    native_max_value = 100.0
    native_step = 1.0
    native_unit_of_measurement = PERCENTAGE
    entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:fan"

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], int | None],
        setter: Callable[[EasyControls3Instance, int], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        self._setter = setter

    @property
    def native_value(self) -> int | None:
        return self._getter(self._device)

    async def async_set_native_value(self, value: float) -> None:
        await self._setter(self._device, int(value))
        await self.coordinator.async_request_refresh()


class AirTempTargetNumber(EasyControls3BaseEntity, NumberEntity):
    device_class = NumberDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    native_min_value = -10.0
    native_max_value = 40.0
    native_step = 1.0
    entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], float | None],
        setter: Callable[[EasyControls3Instance, float], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        self._setter = setter

    @property
    def native_value(self) -> float | None:
        return self._getter(self._device)

    async def async_set_native_value(self, value: float) -> None:
        await self._setter(self._device, value)
        await self.coordinator.async_request_refresh()


class SettingNumber(EasyControls3BaseEntity, NumberEntity):
    entity_category = EntityCategory.CONFIG
    native_step = 1.0

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], float | None],
        setter: Callable[[EasyControls3Instance, float], Awaitable[None]],
        min_value: float,
        max_value: float,
        unit: str | None = None,
        device_class: NumberDeviceClass | None = None,
        icon: str | None = None,
        diagnostic: bool = False,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        self._setter = setter
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        if unit is not None:
            self._attr_native_unit_of_measurement = unit
        if device_class is not None:
            self._attr_device_class = device_class
        if icon is not None:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        return self._getter(self._device)

    async def async_set_native_value(self, value: float) -> None:
        await self._setter(self._device, value)
        await self.coordinator.async_request_refresh()


class RHLimitNumber(EasyControls3BaseEntity, NumberEntity):
    native_min_value = 0.0
    native_max_value = 100.0
    native_step = 1.0
    native_unit_of_measurement = PERCENTAGE
    entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_maxRH"
        self._attr_name = "RH Limit"

    @property
    def native_value(self) -> int | None:
        return self._device.maxRH

    async def async_set_native_value(self, value: float) -> None:
        await self._device.setMaxRH(int(value))
        await self.coordinator.async_request_refresh()


class CO2LimitNumber(EasyControls3BaseEntity, NumberEntity):
    native_min_value = 400.0
    native_max_value = 2000.0
    native_step = 50.0
    native_unit_of_measurement = UnitOfRatio.PARTS_PER_MILLION
    entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_maxCO2"
        self._attr_name = "CO2/VOC Limit"

    @property
    def native_value(self) -> int | None:
        return self._device.maxCO2

    async def async_set_native_value(self, value: float) -> None:
        await self._device.setMaxCO2(int(value))
        await self.coordinator.async_request_refresh()
