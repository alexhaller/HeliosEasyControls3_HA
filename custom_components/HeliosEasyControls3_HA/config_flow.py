"""Config flow for EasyControls3 integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({"host": str})

# Accepts IPv4 addresses or valid hostnames (e.g. helios.local, 192.168.1.10)
_HOST_RE = re.compile(
    r"^("
    r"(\d{1,3}\.){3}\d{1,3}"           # IPv4
    r"|"
    r"([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"  # hostname
    r")$"
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data["host"].strip()
    if not _HOST_RE.match(host):
        raise InvalidHost

    easyControlsInstance = EasyControls3Instance(host)
    result = await easyControlsInstance.test_connection()
    if not result:
        raise CannotConnect

    return {"title": host}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EasyControls3."""

    VERSION = 1

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
                errors["host"] = "invalid_host"
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
