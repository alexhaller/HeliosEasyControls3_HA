from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([KWLOnOffSwitch(coordinator)])


class KWLOnOffSwitch(EasyControls3BaseEntity, SwitchEntity):
    device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_OnOffSwitch"
        self._attr_name = f"{self._device.deviceModel} On/Off"

    @property
    def is_on(self) -> bool | None:
        return self._device.IsOn

    async def async_turn_on(self, **kwargs) -> None:
        await self._device.turnOffOn(requestTurnOff=False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._device.turnOffOn(requestTurnOff=True)
        await self.coordinator.async_request_refresh()
