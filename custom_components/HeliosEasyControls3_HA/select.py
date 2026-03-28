from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import EasyControls3BaseEntity
from .const import DOMAIN
from .KWLStates import KWLState


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([StateSelect(coordinator)])


class StateSelect(EasyControls3BaseEntity, SelectEntity):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_State"
        self._attr_name = f"{self._device.deviceModel} KWL State"
        self._attr_options = [state.name for state in KWLState]

    @property
    def current_option(self) -> str:
        return self._device.instanceState.name

    async def async_select_option(self, option: str) -> None:
        await self._device.switchMode(KWLState[option])
        await self.coordinator.async_request_refresh()
