from datetime import timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .KWLStates import KWLState

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup switch entity."""
    easyConnector = hass.data[DOMAIN][config_entry.entry_id]

    if easyConnector.serialNR is None:
        await easyConnector.readCurrentData()

    async_add_entities([KWLOnOffSwitch(easyConnector)])


class KWLOnOffSwitch(SwitchEntity):
    """On/off switch entity."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the switch entity."""
        self._easyConnector = easyConnector

        self._attr_unique_id = f"{self._easyConnector.serialNR}_OnOffSwitch"
        self._attr_name = f"{self._easyConnector.deviceModel} On Off Switch"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the device on."""
        await self._easyConnector.turnOffOn(requestTurnOff=False)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await self._easyConnector.turnOffOn(requestTurnOff=True)

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._easyConnector.serialNR)}}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._easyConnector.IsAvailable

    async def async_update(self) -> None:
        """Update switch state."""
        await self._easyConnector.readCurrentData()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "KWL on off switch"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._easyConnector.IsOn

    @property
    def device_class(self) -> str:
        """Return the class of this device, from SwitchDeviceClass."""
        return "switch"