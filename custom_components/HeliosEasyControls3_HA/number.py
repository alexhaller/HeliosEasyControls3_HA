from collections.abc import Awaitable, Callable

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance
from .KWLStates import KWLState

PARALLEL_UPDATES = 1


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
                "fireplaceExtractFanSpeed",
                "Individual Extract Fan Speed",
                lambda d: d.FireplaceExtractFanSpeed,
                lambda d, v: d.setFireplaceExtractFanSpeed(v),
            ),
            FanSpeedNumber(
                coordinator,
                "fireplaceSupplyFanSpeed",
                "Individual Supply Fan Speed",
                lambda d: d.FireplaceSupplyFanSpeed,
                lambda d, v: d.setFireplaceSupplyFanSpeed(v),
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
                "fireplaceAirTempTarget",
                "Individual Air Temp Target",
                lambda d: d.FireplaceAirTempTarget,
                lambda d, v: d.setFireplaceAirTempTarget(v),
            ),
            RHLimitNumber(coordinator),
            CO2LimitNumber(coordinator),
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
    native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
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
