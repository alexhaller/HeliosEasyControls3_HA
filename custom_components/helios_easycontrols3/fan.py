from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import (
    EasyControls3BaseEntity,
    EasyControls3ConfigEntry,
    EasyControls3Coordinator,
)
from .KWLStates import KWLState

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EasyControls3ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = config_entry.runtime_data
    async_add_entities([VentilationFan(coordinator)])


class VentilationFan(EasyControls3BaseEntity, FanEntity):
    """The ventilation unit as one fan: power, operating mode and fan speed.

    It bundles what the On/Off switch, the KWL State select and the per-mode
    fan speed numbers do, so voice assistants and fan cards can drive the unit.
    """

    _attr_icon = "mdi:hvac"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_Fan"
        # The main feature of the device: the entity takes the device name
        self._attr_name = None
        self._attr_preset_modes = [state.name for state in KWLState]

    @property
    def is_on(self) -> bool | None:
        return self._device.IsOn

    @property
    def percentage(self) -> int | None:
        if self._device.IsOn is False:
            return 0
        return self._device.CurrentFanSpeed

    @property
    def preset_mode(self) -> str | None:
        state = self._device.instanceState
        return state.name if state is not None else None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if not self._device.IsOn:
            await self._device.turnOffOn(requestTurnOff=False)
        if preset_mode is not None:
            await self._device.switchMode(KWLState[preset_mode])
        if percentage:
            await self._set_speed(
                percentage, KWLState[preset_mode] if preset_mode else None
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.turnOffOn(requestTurnOff=True)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._device.switchMode(KWLState[preset_mode])
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        await self._set_speed(percentage, None)
        await self.coordinator.async_request_refresh()

    async def _set_speed(self, percentage: int, mode: KWLState | None) -> None:
        """Set the fan speed of the given mode, or of the active one."""
        mode = mode or self._device.instanceState
        if mode is None or mode is KWLState.Individual:
            # Individual mode has separate supply and extract speeds
            raise ServiceValidationError(
                "The fan speed of the Individual mode is set with the "
                "Individual Supply/Extract Fan Speed numbers"
            )
        await self._device.setFanSpeed(percentage, mode)
