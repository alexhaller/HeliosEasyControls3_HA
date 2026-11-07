from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN
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
            StateSelect(coordinator),
            TempControlModeSelect(coordinator),
            HeatExchangerSelect(coordinator),
            HumidityControlModeSelect(coordinator),
            TimedFunctionModeSelect(coordinator),
        ]
    )


class StateSelect(EasyControls3BaseEntity, SelectEntity):
    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_State"
        self._attr_name = "KWL State"
        self._attr_options = [state.name for state in KWLState]

    @property
    def current_option(self) -> str | None:
        state = self._device.instanceState
        return state.name if state is not None else None

    async def async_select_option(self, option: str) -> None:
        await self._device.switchMode(KWLState[option])
        await self.coordinator.async_request_refresh()


class TempControlModeSelect(EasyControls3BaseEntity, SelectEntity):
    entity_category = EntityCategory.CONFIG

    # A_CYC_SUPPLY_HEATING_ADJUST_MODE: supply air / extract air / cooling mode
    _VALUE_TO_OPTION: ClassVar[dict[int, str]] = {
        0: "Supply",
        1: "Extract",
        2: "Extract+",
    }
    _OPTION_TO_VALUE: ClassVar[dict[str, int]] = {
        v: k for k, v in _VALUE_TO_OPTION.items()
    }

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_TempControlMode"
        self._attr_name = "Temperature Control Mode"
        self._attr_options = list(self._VALUE_TO_OPTION.values())

    @property
    def current_option(self) -> str | None:
        mode = self._device.supplyHeatingAdjustMode
        if mode is None:
            return None
        return self._VALUE_TO_OPTION.get(mode)

    async def async_select_option(self, option: str) -> None:
        await self._device.setSupplyHeatingAdjustMode(self._OPTION_TO_VALUE[option])
        await self.coordinator.async_request_refresh()


class HeatExchangerSelect(EasyControls3BaseEntity, SelectEntity):
    entity_category = EntityCategory.CONFIG

    # A_CYC_CELL_TYPE: 0=aluminium is not offered on Helios units
    _VALUE_TO_OPTION: ClassVar[dict[int, str]] = {1: "Plastic", 2: "Enthalpy"}
    _OPTION_TO_VALUE: ClassVar[dict[str, int]] = {
        v: k for k, v in _VALUE_TO_OPTION.items()
    }

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_heatExchanger"
        self._attr_name = "Heat Exchanger"
        self._attr_options = list(self._VALUE_TO_OPTION.values())

    @property
    def current_option(self) -> str | None:
        value = self._device.heatExchanger
        if value is None:
            return None
        return self._VALUE_TO_OPTION.get(value)

    async def async_select_option(self, option: str) -> None:
        await self._device.setHeatExchanger(self._OPTION_TO_VALUE[option])
        await self.coordinator.async_request_refresh()


class HumidityControlModeSelect(EasyControls3BaseEntity, SelectEntity):
    entity_category = EntityCategory.CONFIG

    # A_CYC_RH_LEVEL_MODE
    _VALUE_TO_OPTION: ClassVar[dict[int, str]] = {0: "Automatic", 1: "Manual"}
    _OPTION_TO_VALUE: ClassVar[dict[str, int]] = {
        v: k for k, v in _VALUE_TO_OPTION.items()
    }

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_rhLevelMode"
        self._attr_name = "Humidity Control Mode"
        self._attr_options = list(self._VALUE_TO_OPTION.values())

    @property
    def current_option(self) -> str | None:
        value = self._device.rhLevelMode
        if value is None:
            return None
        return self._VALUE_TO_OPTION.get(value)

    async def async_select_option(self, option: str) -> None:
        await self._device.setRhLevelMode(self._OPTION_TO_VALUE[option])
        await self.coordinator.async_request_refresh()


class TimedFunctionModeSelect(EasyControls3BaseEntity, SelectEntity):
    entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:airplane-clock"

    # A_CYC_TIMED_FUNCTION_MODE: the mode the unit holds during the date range
    _VALUE_TO_OPTION: ClassVar[dict[int, str]] = {
        0: "At Home",
        1: "Away",
        2: "Standby",
    }
    _OPTION_TO_VALUE: ClassVar[dict[str, int]] = {
        v: k for k, v in _VALUE_TO_OPTION.items()
    }

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_timedFunctionMode"
        self._attr_name = "Timed Function Mode"
        self._attr_options = list(self._VALUE_TO_OPTION.values())

    @property
    def current_option(self) -> str | None:
        value = self._device.timedFunctionMode
        if value is None:
            return None
        return self._VALUE_TO_OPTION.get(value)

    async def async_select_option(self, option: str) -> None:
        await self._device.setTimedFunctionMode(self._OPTION_TO_VALUE[option])
        await self.coordinator.async_request_refresh()
