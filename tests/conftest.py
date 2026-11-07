"""Fixtures for the Helios easyControls 3.0 tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from custom_components.helios_easycontrols3.EasyControls3Instance import (
    EasyControls3Instance,
)

pytest_plugins = "pytest_homeassistant_custom_component"

SERIAL = 12345
HOST = "192.168.1.126"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable the integration under custom_components."""


@pytest.fixture
def mock_unit() -> Generator[None]:
    """Answer every poll as a unit with a fixed serial, without any network."""

    async def read(self: EasyControls3Instance) -> None:
        self._SerialNR = SERIAL
        self._deviceModel = "KWL 360 W ET"
        self._deviceType = "KWL"

    with (
        patch.object(EasyControls3Instance, "readCurrentData", read),
        patch.object(EasyControls3Instance, "test_connection", return_value=True),
    ):
        yield
