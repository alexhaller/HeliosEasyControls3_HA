"""Tests for EasyControls3 device communication."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.HeliosEasyControls3_HA.EasyControls3Instance import (
    EasyControls3Instance,
)
from custom_components.HeliosEasyControls3_HA.KWLStates import KWLState


@pytest.fixture
def easy_controls_instance():
    """Create an EasyControls3Instance for testing."""
    return EasyControls3Instance("192.168.1.100")


@pytest.mark.asyncio
async def test_instance_initialization(easy_controls_instance):
    """Test that instance initializes with correct defaults."""
    assert easy_controls_instance._url == "ws://192.168.1.100:80"
    assert easy_controls_instance._deviceModel is None
    assert easy_controls_instance._isAvailable is True


@pytest.mark.asyncio
async def test_check_fan_speed_limit(easy_controls_instance):
    """Test fan speed limit validation."""
    assert easy_controls_instance.checkFanSpeedLimit(0) == 1
    assert easy_controls_instance.checkFanSpeedLimit(50) == 50
    assert easy_controls_instance.checkFanSpeedLimit(100) == 100
    assert easy_controls_instance.checkFanSpeedLimit(150) == 100


@pytest.mark.asyncio
async def test_create_fan_speed_plain_request(easy_controls_instance):
    """Test fan speed hex string generation."""
    assert easy_controls_instance.createFanSpeedPlainRequestString(1) == "01"
    assert easy_controls_instance.createFanSpeedPlainRequestString(15) == "0f"
    assert easy_controls_instance.createFanSpeedPlainRequestString(50) == "32"


@pytest.mark.asyncio
async def test_create_fan_speed_modded_request(easy_controls_instance):
    """Test modded fan speed string with offset."""
    # AtHome offset is 24
    result = easy_controls_instance.createFanSpeedModdedRequestString(
        25, KWLState.AtHome
    )
    assert result == "31"  # 25 + 24 = 49 = 0x31

    # Away offset is 18
    result = easy_controls_instance.createFanSpeedModdedRequestString(
        25, KWLState.Away
    )
    assert result == "2b"  # 25 + 18 = 43 = 0x2b

    # Intensive offset is 30
    result = easy_controls_instance.createFanSpeedModdedRequestString(
        25, KWLState.Intensive
    )
    assert result == "37"  # 25 + 30 = 55 = 0x37


@pytest.mark.asyncio
async def test_switch_mode_invalid_state(easy_controls_instance):
    """Test that switching to invalid state raises error."""
    with patch.object(
        easy_controls_instance, "_exchangeData", new_callable=AsyncMock
    ):
        with pytest.raises(TypeError, match="wantedKWLState must be an instance"):
            await easy_controls_instance.switchMode("invalid_state")


@pytest.mark.asyncio
async def test_parse_data_basic(easy_controls_instance):
    """Test parsing device response with mock data."""
    # Create mock response data (simplified)
    mock_data = bytearray(500)

    # Set device model at offset 17*2+1 (index 35)
    mock_data[35] = 0

    # Set device type at offset 16*2+1 (index 33)
    mock_data[33] = 0

    # Set serial number at offsets 14*2, 14*2+1, 15*2, 15*2+1
    mock_data[28] = 0x00
    mock_data[29] = 0x00
    mock_data[30] = 0x12
    mock_data[31] = 0x34

    # Set operating mode (offsets 107, 110, 111)
    mock_data[214] = 0  # state
    mock_data[220] = 0  # boost
    mock_data[222] = 0  # fire

    # Set fan speeds
    mock_data[129] = 50

    # Set on/off state at offset 217
    mock_data[217] = 0  # Device is on

    # Set CO2 at offsets 182-183
    mock_data[182] = 0x05
    mock_data[183] = 0xDC  # 0x05DC = 1500

    easy_controls_instance._parseData(mock_data)

    assert easy_controls_instance.CurrentFanSpeed == 50
    assert easy_controls_instance.IsOn is True
    assert easy_controls_instance.CO2Value == 1500
