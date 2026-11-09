"""Diagnostics dump the parsed device state without host and serial."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from custom_components.helios_easycontrols3 import EasyControls3Coordinator
from custom_components.helios_easycontrols3.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import HOST
from .test_device import _frame, _parsed


async def test_diagnostics_are_json_and_redacted() -> None:
    coordinator = MagicMock(spec=EasyControls3Coordinator)
    coordinator.data = _parsed(_frame())
    coordinator.data._SerialNR = 2336231257
    coordinator.last_update_success = True
    entry = MagicMock()
    entry.data = {"host": HOST}
    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(MagicMock(), entry)

    text = json.dumps(diagnostics)
    assert HOST not in text
    assert "2336231257" not in text
    assert diagnostics["device"]["firmwareVersion"] == [1, 0, 29]
    assert diagnostics["device"]["cfSupported"] is True
    assert "lock" not in diagnostics["device"]
