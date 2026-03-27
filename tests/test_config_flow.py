"""Tests for config flow."""
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.HeliosEasyControls3_HA.config_flow import (
    ConfigFlow,
    CannotConnect,
    InvalidHost,
    validate_input,
)
from custom_components.HeliosEasyControls3_HA.const import DOMAIN


@pytest.mark.asyncio
async def test_validate_input_invalid_host(hass):
    """Test validation rejects invalid IP addresses."""
    with pytest.raises(InvalidHost):
        await validate_input(hass, {"host": "not.an.ip.address"})

    with pytest.raises(InvalidHost):
        await validate_input(hass, {"host": "999.999.999.999"})


@pytest.mark.asyncio
async def test_validate_input_connection_error(hass):
    """Test validation handles connection errors."""
    with patch(
        "custom_components.HeliosEasyControls3_HA.config_flow.EasyControls3Instance"
    ) as mock_instance_class:
        mock_instance = AsyncMock()
        mock_instance.test_connection.return_value = False
        mock_instance_class.return_value = mock_instance

        with pytest.raises(CannotConnect):
            await validate_input(hass, {"host": "192.168.1.100"})


@pytest.mark.asyncio
async def test_validate_input_success(hass):
    """Test successful validation."""
    with patch(
        "custom_components.HeliosEasyControls3_HA.config_flow.EasyControls3Instance"
    ) as mock_instance_class:
        mock_instance = AsyncMock()
        mock_instance.test_connection.return_value = True
        mock_instance_class.return_value = mock_instance

        result = await validate_input(hass, {"host": "192.168.1.100"})
        assert result["title"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_config_flow_step_user_invalid_host(hass):
    """Test config flow rejects invalid host input."""
    flow = ConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user({"host": "invalid"})

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "host" in result["errors"]


@pytest.mark.asyncio
async def test_config_flow_step_user_connection_error(hass):
    """Test config flow handles connection errors."""
    with patch(
        "custom_components.HeliosEasyControls3_HA.config_flow.EasyControls3Instance"
    ) as mock_instance_class:
        mock_instance = AsyncMock()
        mock_instance.test_connection.return_value = False
        mock_instance_class.return_value = mock_instance

        flow = ConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user({"host": "192.168.1.100"})

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert "base" in result["errors"]
        assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_config_flow_step_user_success(hass):
    """Test successful config flow."""
    with patch(
        "custom_components.HeliosEasyControls3_HA.config_flow.EasyControls3Instance"
    ) as mock_instance_class:
        mock_instance = AsyncMock()
        mock_instance.test_connection.return_value = True
        mock_instance_class.return_value = mock_instance

        flow = ConfigFlow()
        flow.hass = hass
        flow.async_create_entry = AsyncMock()

        await flow.async_step_user({"host": "192.168.1.100"})

        assert flow.async_create_entry.called
