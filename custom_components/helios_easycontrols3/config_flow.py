"""Config flow for EasyControls3 integration."""

import logging
import re
from typing import Any

import probatio
from homeassistant import config_entries, exceptions
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = probatio.Schema({"host": str})

# Accepts IPv4 addresses (each octet 0-255) or valid hostnames (e.g. helios.local, 192.168.1.10)
_OCTET = r"(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)"
_HOST_RE = re.compile(
    r"^("
    + _OCTET
    + r"\."
    + _OCTET
    + r"\."
    + _OCTET
    + r"\."
    + _OCTET  # IPv4
    + r"|"
    + r"([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"  # hostname
    + r")$"
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data["host"].strip().lower()
    if not _HOST_RE.match(host):
        raise InvalidHost

    easyControlsInstance = EasyControls3Instance(host)
    result = await easyControlsInstance.test_connection()
    if not result:
        raise CannotConnect

    return {"title": host, "serial": easyControlsInstance.serialNR}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EasyControls3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                errors["host"] = "invalid_host"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Outside the try: the abort is an exception, not an error
                await self.async_set_unique_id(info["title"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"], data={"host": info["title"]}
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Point the entry at a new host without losing its device and entities.

        The unique_id stays the host, so it is moved along with it. The unit
        found at the new host must be the one the entry already has a device
        for (identified by its serial number), otherwise the entities would be
        silently re-pointed at a different unit.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                errors["host"] = "invalid_host"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                host = info["title"]
                if any(
                    other.unique_id == host
                    for other in self._async_current_entries(include_ignore=True)
                    if other.entry_id != entry.entry_id
                ):
                    return self.async_abort(reason="already_configured")
                known = {
                    identifier
                    for device in dr.async_entries_for_config_entry(
                        dr.async_get(self.hass), entry.entry_id
                    )
                    for domain, identifier in device.identifiers
                    if domain == DOMAIN
                }
                if known and str(info["serial"]) not in known:
                    errors["base"] = "wrong_device"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=host,
                        # Keep a title the user chose, follow one that is the host
                        title=host
                        if entry.title == entry.data["host"]
                        else entry.title,
                        data_updates={"host": host},
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        "host", default=(user_input or entry.data)["host"]
                    ): str
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Recreate an entry of the legacy domain without contacting the unit.

        The unit may be offline at startup; the entry already proved it works.
        """
        await self.async_set_unique_id(import_data["host"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=import_data["title"], data={"host": import_data["host"]}
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
