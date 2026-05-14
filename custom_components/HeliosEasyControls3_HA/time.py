from collections.abc import Awaitable, Callable
from datetime import time

from homeassistant.components.time import TimeEntity
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
            DurationEntity(
                coordinator,
                "intensiveDuration",
                "Intensive Mode Duration",
                lambda d: d.IntensivDuration,
                lambda d, v: d.setIntensiveDuration(v),
            ),
            DurationEntity(
                coordinator,
                "extraModeDuration",
                "Extra Mode Duration",
                lambda d: d.ExtraModeDuration,
                lambda d, v: d.setExtraModeDuration(v),
            ),
            DurationEntity(
                coordinator,
                "fireplaceModeDuration",
                "Individual Mode Duration",
                lambda d: d.FireplaceModeDuration,
                lambda d, v: d.setFireplaceModeDuration(v),
            ),
        ]
    )


class DurationEntity(EasyControls3BaseEntity, TimeEntity):
    entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], time | None],
        setter: Callable[[EasyControls3Instance, time], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        self._setter = setter

    @property
    def native_value(self) -> time | None:
        return self._getter(self._device)

    async def async_set_value(self, value: time) -> None:
        await self._setter(self._device, value)
        await self.coordinator.async_request_refresh()
