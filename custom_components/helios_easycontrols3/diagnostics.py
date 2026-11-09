"""Diagnostics for the Helios easyControls 3.0 integration."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import EasyControls3ConfigEntry

TO_REDACT = {"host", "SerialNR", "url"}


def _plain(value: Any) -> Any:
    """Make a parsed device value JSON friendly."""
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EasyControls3ConfigEntry
) -> dict[str, Any]:
    """Return everything the last poll parsed from the unit.

    The reply frame carries no passwords: the integration never reads the
    access or user password registers.
    """
    coordinator = entry.runtime_data
    device = coordinator.data
    return async_redact_data(
        {
            "entry": {"data": dict(entry.data)},
            "last_update_success": coordinator.last_update_success,
            "device": {
                key.lstrip("_"): _plain(value)
                for key, value in vars(device).items()
                if key != "_lock"
            },
        },
        TO_REDACT,
    )
