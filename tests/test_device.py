"""Parsing and command building of the device layer, on a synthetic reply frame."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from websockets.exceptions import ConnectionClosedError

from custom_components.helios_easycontrols3.EasyControls3Instance import (
    _WRITE_OK,
    EasyControls3Instance,
    WriteRejected,
    _minutes_to_time,
)
from custom_components.helios_easycontrols3.KWLStates import KWLState

from .conftest import HOST

# Range length markers of the reply layout, as buffer offset -> word count
MARKERS = {
    0: 36,
    63: 43,
    106: 25,
    131: 7,
    138: 7,
    145: 7,
    152: 30,
    182: 76,
    258: 23,
    281: 16,
    297: 200,
    497: 169,
    666: 39,
}


def _frame(
    version: tuple[int, ...] = (1, 0, 29), markers: dict[int, int] | None = None
) -> bytes:
    words = [0] * 705
    for offset, length in (markers or MARKERS).items():
        words[offset] = length
    words[248] = 1  # filter changed day
    words[249] = 1  # filter changed month
    words[284] = 50  # home supply base airflow
    data = bytearray(b"".join(w.to_bytes(2, "big") for w in words))
    # The firmware version is the one little-endian field, right-aligned in buf 2-10
    for index, part in enumerate(version[::-1]):
        offset = 10 - index
        data[offset * 2 : offset * 2 + 2] = part.to_bytes(2, "little")
    return bytes(data)


def _parsed(data: bytes) -> EasyControls3Instance:
    device = EasyControls3Instance(HOST)
    device._parseData(data)
    return device


def test_firmware_version() -> None:
    assert _parsed(_frame((1, 0, 29))).firmwareVersion == "1.0.29"


@pytest.mark.parametrize(
    ("version", "supported"),
    [((1, 0, 9), False), ((1, 0, 28), False), ((1, 0, 29), True), ((1, 1, 0), True)],
)
def test_constant_flow_only_on_verified_firmware(
    version: tuple[int, ...], supported: bool
) -> None:
    """0x8001-0x8006 are self-test registers on 1.0.9, setpoints from 1.0.29."""
    device = _parsed(_frame(version))
    assert device.cfSupported is supported
    assert device.cfBaseAirflow("home_supply") == (50 if supported else None)


def test_constant_flow_needs_its_range_marker() -> None:
    assert not _parsed(_frame(markers={**MARKERS, 281: 17})).cfSupported


def test_extended_block_skipped_when_layout_differs() -> None:
    assert _parsed(_frame()).TimedFunctionEnabled is False
    assert _parsed(_frame(markers={**MARKERS, 497: 170})).TimedFunctionEnabled is None


def test_unknown_device_codes(caplog: pytest.LogCaptureFixture) -> None:
    data = bytearray(_frame())
    data[17 * 2 + 1] = 250  # machine model
    device = EasyControls3Instance(HOST)
    device._parseData(bytes(data))
    device._parseData(bytes(data))

    assert device.deviceModel == "Unknown model (250)"
    assert caplog.text.count("Unknown Helios device codes") == 1


@pytest.mark.parametrize(
    ("code", "expected"), [(107, "40055-005"), (106, "Unknown type (106)")]
)
def test_device_type_beyond_the_table(code: int, expected: str) -> None:
    """Confirmed codes past the table are named; the gap stays unknown."""
    data = bytearray(_frame())
    data[16 * 2 + 1] = code  # machine type
    assert _parsed(bytes(data)).deviceType == expected


async def test_individual_mode_uses_configured_duration() -> None:
    device = _parsed(_frame())
    device._individualModeDuration = datetime.time(0, 15)
    device._exchangeData = AsyncMock(return_value=_WRITE_OK)

    await device.switchMode(KWLState.Individual)

    sent = device._exchangeData.await_args.args[0]
    assert device._build_write_command((0x1204, 0), (0x1205, 15)) == sent


@pytest.mark.parametrize("unit", [0, 1, 2, 255, 256, 65535])
def test_constant_flow_unit_reads_full_word(unit: int) -> None:
    data = bytearray(_frame())
    data[400:402] = unit.to_bytes(2, "big")
    assert _parsed(bytes(data)).cfFanSpeedUnit == unit


@pytest.mark.parametrize(
    "data",
    [
        _frame((1, 0, 9)),  # Reserved zero must not be interpreted as l/s.
        _frame((1, 0, 28)),
        _frame(()),  # Missing firmware version.
        _frame(markers={**MARKERS, 281: 17}),
    ],
)
def test_constant_flow_unit_cleared_when_unsupported(data: bytes) -> None:
    device = _parsed(_frame())
    assert device.cfFanSpeedUnit == 0
    device._parseData(data)
    assert device.cfFanSpeedUnit is None


def test_constant_flow_unit_before_first_reply() -> None:
    assert EasyControls3Instance(HOST).cfFanSpeedUnit is None


@pytest.mark.parametrize("word", [248, 249])
def test_unset_filter_date_does_not_break_parsing(word: int) -> None:
    """A never-set filter date (day 248 or month 249 = 0) must not fail the parse."""
    data = bytearray(_frame())
    data[word * 2 + 1] = 0
    device = _parsed(bytes(data))
    assert device.filterChanged is None
    assert device.filterDue is None
    assert device.cfSupported  # parsing went on past the date


def test_set_filter_date_still_parsed() -> None:
    data = bytearray(_frame())
    data[250 * 2 + 1] = 26  # year since 2000
    device = _parsed(bytes(data))
    assert device.filterChanged == datetime.date(2026, 1, 1)
    assert device.filterDue == datetime.date(2026, 1, 1) + datetime.timedelta(
        days=device.filterInterval or 0
    )


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, datetime.time(0, 0)),
        (1439, datetime.time(23, 59)),
        (1440, None),
        (65535, None),
    ],
)
def test_minutes_to_time_out_of_range(
    minutes: int, expected: datetime.time | None
) -> None:
    assert _minutes_to_time(minutes) == expected


@pytest.mark.parametrize(
    ("word", "attribute"),
    [
        (198, "ExtraModeDuration"),
        (246, "IntensivDuration"),
        (247, "IndividualModeDuration"),
    ],
)
def test_out_of_range_duration_does_not_break_parsing(
    word: int, attribute: str
) -> None:
    """1440 min = 24 h does not fit a time of day; the rest must still parse."""
    data = bytearray(_frame())
    data[word * 2 : word * 2 + 2] = (1440).to_bytes(2, "big")
    device = _parsed(bytes(data))
    assert getattr(device, attribute) is None
    assert device.filterChanged == datetime.date(2000, 1, 1)


async def test_switch_to_unknown_duration_is_a_clean_error() -> None:
    data = bytearray(_frame())
    data[246 * 2 : 246 * 2 + 2] = (1440).to_bytes(2, "big")
    device = _parsed(bytes(data))
    device._exchangeData = AsyncMock(return_value=_WRITE_OK)
    with pytest.raises(HomeAssistantError) as excinfo:
        await device.switchMode(KWLState.Intensive)
    assert excinfo.value.translation_key == "intensive_duration_unknown"
    device._exchangeData.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [ConnectionRefusedError(), TimeoutError(), ConnectionClosedError(None, None)],
)
async def test_test_connection_false_when_unreachable(error: Exception) -> None:
    device = EasyControls3Instance(HOST)
    device._exchangeData = AsyncMock(side_effect=error)
    assert await device.test_connection() is False


async def test_test_connection_false_on_truncated_reply() -> None:
    device = EasyControls3Instance(HOST)
    device._exchangeData = AsyncMock(return_value=b"\x00\x01")
    assert await device.test_connection() is False


async def test_test_connection_true_on_valid_reply() -> None:
    device = EasyControls3Instance(HOST)
    device._exchangeData = AsyncMock(return_value=_frame())
    assert await device.test_connection() is True


async def test_test_connection_does_not_swallow_bugs() -> None:
    device = EasyControls3Instance(HOST)
    device._exchangeData = AsyncMock(side_effect=ValueError("bug"))
    with pytest.raises(ValueError, match="bug"):
        await device.test_connection()


async def test_unacknowledged_write_is_a_translated_error() -> None:
    device = EasyControls3Instance(HOST)
    with pytest.raises(WriteRejected) as excinfo:
        device._check_write_response(b"\x00\x01", "mode switch")
    assert excinfo.value.translation_key == "write_rejected"
    assert excinfo.value.translation_placeholders == {
        "context": "mode switch",
        "response": "0001",
    }
