"""The fan entity bundles power, operating mode and fan speed."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.helios_easycontrols3 import EasyControls3Coordinator
from custom_components.helios_easycontrols3.fan import (
    VentilationFan,
    async_setup_entry,
)
from custom_components.helios_easycontrols3.KWLStates import KWLState

from .test_device import _frame, _parsed


async def _fan(
    state: KWLState = KWLState.AtHome, on: bool = True, speed: int = 40
) -> tuple[EasyControls3Coordinator, VentilationFan]:
    coordinator = MagicMock(spec=EasyControls3Coordinator)
    device = _parsed(_frame())
    device._instanceState = state
    device._isOn = on
    device._CurrentFanSpeed = speed
    device.turnOffOn = AsyncMock()
    device.switchMode = AsyncMock()
    device.setFanSpeed = AsyncMock()
    coordinator.data = device
    coordinator.async_request_refresh = AsyncMock()
    hass = MagicMock()
    entry = MagicMock()
    entry.runtime_data = coordinator
    add_entities = MagicMock()
    await async_setup_entry(hass, entry, add_entities)
    (fan,) = add_entities.call_args.args[0]
    return coordinator, fan


async def test_state_follows_the_device() -> None:
    _, fan = await _fan(KWLState.Away, speed=35)

    assert fan.is_on is True
    assert fan.percentage == 35
    assert fan.preset_mode == "Away"
    assert fan.preset_modes == ["AtHome", "Away", "Intensive", "Individual"]
    assert fan.name is None


async def test_switched_off_unit_has_no_speed() -> None:
    _, fan = await _fan(on=False, speed=20)

    assert fan.is_on is False
    assert fan.percentage == 0


async def test_percentage_sets_the_speed_of_the_active_mode() -> None:
    coordinator, fan = await _fan(KWLState.Away)

    await fan.async_set_percentage(55)

    coordinator.data.setFanSpeed.assert_awaited_once_with(55, KWLState.Away)
    coordinator.async_request_refresh.assert_awaited()


async def test_zero_percent_switches_the_unit_off() -> None:
    coordinator, fan = await _fan()

    await fan.async_set_percentage(0)

    coordinator.data.turnOffOn.assert_awaited_once_with(requestTurnOff=True)
    coordinator.data.setFanSpeed.assert_not_awaited()


async def test_individual_mode_speed_is_not_a_single_value() -> None:
    _, fan = await _fan(KWLState.Individual)

    with pytest.raises(ServiceValidationError):
        await fan.async_set_percentage(50)


async def test_preset_mode_switches_the_mode() -> None:
    coordinator, fan = await _fan()

    await fan.async_set_preset_mode("Intensive")

    coordinator.data.switchMode.assert_awaited_once_with(KWLState.Intensive)


async def test_turn_on_powers_up_then_applies_mode_and_speed() -> None:
    coordinator, fan = await _fan(on=False)
    device = coordinator.data

    await fan.async_turn_on(percentage=60, preset_mode="Away")

    device.turnOffOn.assert_awaited_once_with(requestTurnOff=False)
    device.switchMode.assert_awaited_once_with(KWLState.Away)
    device.setFanSpeed.assert_awaited_once_with(60, KWLState.Away)


async def test_turn_on_a_running_unit_changes_nothing_else() -> None:
    coordinator, fan = await _fan()

    await fan.async_turn_on()

    coordinator.data.turnOffOn.assert_not_awaited()
    coordinator.data.switchMode.assert_not_awaited()
    coordinator.data.setFanSpeed.assert_not_awaited()
