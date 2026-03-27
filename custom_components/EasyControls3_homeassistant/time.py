from datetime import time, timedelta

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .KWLStates import KWLState

SCAN_INTERVAL = timedelta(seconds=60)
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup time entity."""
    easyConnector = hass.data[DOMAIN][config_entry.entry_id]

    if easyConnector.serialNR is None:
        await easyConnector.readCurrentData()

    async_add_entities([IntensiveDuration(easyConnector)])


class IntensiveDuration(TimeEntity):
    """Intensive mode duration time entity."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the time entity."""
        self._easyConnector = easyConnector

        self._attr_unique_id = f"{self._easyConnector.serialNR}_intensiveDuration"
        self._attr_name = f"{self._easyConnector.deviceModel} Intensive Mode Duration"
        self.native_value = self._easyConnector.IntensivDuration

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""
        await self._easyConnector.setIntensiveDuration(value)

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._easyConnector.serialNR)}}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._easyConnector.IsAvailable

    async def async_update(self) -> None:
        """Update the time value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.IntensivDuration

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Time for the intensive mode"
