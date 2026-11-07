import datetime
from collections.abc import Awaitable, Callable

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN
from .EasyControls3Instance import EasyControls3Instance

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            SettingDate(
                coordinator,
                "timedFunctionStart",
                "Timed Function Start",
                lambda d: d.TimedFunctionStart,
                lambda d, v: d.setTimedFunctionStart(v),
            ),
            SettingDate(
                coordinator,
                "timedFunctionEnd",
                "Timed Function End",
                lambda d: d.TimedFunctionEnd,
                lambda d, v: d.setTimedFunctionEnd(v),
            ),
        ]
    )


class SettingDate(EasyControls3BaseEntity, DateEntity):
    entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calendar-range"

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], datetime.date | None],
        setter: Callable[[EasyControls3Instance, datetime.date], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        self._setter = setter

    @property
    def native_value(self) -> datetime.date | None:
        return self._getter(self._device)

    async def async_set_value(self, value: datetime.date) -> None:
        await self._setter(self._device, value)
        await self.coordinator.async_request_refresh()
