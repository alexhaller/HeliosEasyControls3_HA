"""Constant-flow labels track the device without changing values or writes."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.helios_easycontrols3 import EasyControls3Coordinator
from custom_components.helios_easycontrols3.const import DOMAIN
from custom_components.helios_easycontrols3.number import (
    ConstantFlowNumber,
    async_setup_entry,
)

from .test_device import MARKERS, _frame, _parsed


async def _cf_entities() -> tuple[EasyControls3Coordinator, list[ConstantFlowNumber]]:
    coordinator = MagicMock(spec=EasyControls3Coordinator)
    coordinator.data = _parsed(_frame())
    coordinator.async_request_refresh = AsyncMock()
    hass = MagicMock()
    entry = MagicMock()
    hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    add_entities = MagicMock()
    await async_setup_entry(hass, entry, add_entities)
    return coordinator, [
        entity
        for entity in add_entities.call_args.args[0]
        if isinstance(entity, ConstantFlowNumber)
    ]


async def test_all_constant_flow_numbers_follow_unit_changes() -> None:
    coordinator, entities = await _cf_entities()
    assert len(entities) == 6
    keys = (
        "away_supply",
        "away_extract",
        "home_supply",
        "home_extract",
        "boost_supply",
        "boost_extract",
    )
    ids = [f"{coordinator.data.serialNR}_cfBaseAirflow_{key}" for key in keys]
    for code, unit in ((0, "L/s"), (1, "m³/h"), (2, "%"), (256, None), (0, "L/s")):
        data = bytearray(_frame())
        data[400:402] = code.to_bytes(2, "big")
        for index in range(6):
            data[(282 + index) * 2 : (283 + index) * 2] = (30 + index).to_bytes(
                2, "big"
            )
        coordinator.data._parseData(bytes(data))
        assert [entity.native_unit_of_measurement for entity in entities] == [unit] * 6
        assert [entity.native_value for entity in entities] == list(range(30, 36))
        assert [entity.unique_id for entity in entities] == ids
        assert all(entity.native_min_value == 0 for entity in entities)
        assert all(entity.native_max_value == 300 for entity in entities)

    coordinator.data._cfFanSpeedUnit = None
    assert all(entity.native_unit_of_measurement is None for entity in entities)

    for data in (_frame((1, 0, 9)), _frame(markers={**MARKERS, 281: 17})):
        coordinator.data._parseData(_frame())
        assert all(entity.native_unit_of_measurement == "L/s" for entity in entities)
        coordinator.data._parseData(data)
        assert all(entity.native_unit_of_measurement is None for entity in entities)


@pytest.mark.parametrize("unit", [0, 1, 2, 255])
async def test_constant_flow_writes_still_use_raw_values(unit: int) -> None:
    coordinator, entities = await _cf_entities()
    data = bytearray(_frame())
    data[400:402] = unit.to_bytes(2, "big")
    coordinator.data._parseData(bytes(data))
    coordinator.data._set_int = AsyncMock()
    for index, entity in enumerate(entities):
        await entity.async_set_native_value(42)
        coordinator.data._set_int.assert_awaited_with(0x8001 + index, 42)
    assert coordinator.async_request_refresh.await_count == 6
