from datetime import timedelta

from homeassistant.components.select import SelectEntity
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
    """Setup select entity."""
    easyConnector = hass.data[DOMAIN][config_entry.entry_id]

    if easyConnector.serialNR is None:
        await easyConnector.readCurrentData()

    async_add_entities([StateSelect(easyConnector)])


class StateSelect(SelectEntity):
    """State selection entity."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the select entity."""
        self._easyConnector = easyConnector

        self._attr_unique_id = f"{self._easyConnector.serialNR}_State"
        self._attr_name = f"{self._easyConnector.deviceModel} KWL State"
        self._attr_options = [state.name for state in KWLState]
        self._attr_current_option = str(self._easyConnector.instanceState.name)

    async def async_select_option(self, option: str) -> None:
        """Update the selected option."""
        await self._easyConnector.switchMode(KWLState[option])

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._easyConnector.serialNR)}}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._easyConnector.IsAvailable

    async def async_update(self) -> None:
        """Update the current selected option."""
        await self._easyConnector.readCurrentData()
        self._attr_current_option = str(self._easyConnector.instanceState.name)

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Select State of the KWL"
