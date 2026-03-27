"""Config flow for EasyControls3 integration."""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance

_LOGGER = logging.getLogger(__name__)


DATA_SCHEMA = vol.Schema({("host"): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.
    try:
        ipaddress.IPv4Address(data["host"])
    except ValueError:
        raise InvalidHost

    easyControlsInstance = EasyControls3Instance(data["host"])
    result = await easyControlsInstance.test_connection()
    if not result:
        raise CannotConnect

    return {"title": data["host"]}


class ConfigFlow(config_entries.ConfigFlow):
    """Config flow for EasyControls3."""

    VERSION = 1
    domain = DOMAIN

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                errors["host"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
