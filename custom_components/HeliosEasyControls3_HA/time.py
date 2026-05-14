from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            IntensiveDuration(coordinator),
            ExtraModeDuration(coordinator),
            FireplaceModeDuration(coordinator),
        ]
    )


class IntensiveDuration(EasyControls3BaseEntity, TimeEntity):
    entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_intensiveDuration"
        self._attr_name = "Intensive Mode Duration"

    @property
    def native_value(self) -> time | None:
        return self._device.IntensivDuration

    async def async_set_value(self, value: time) -> None:
        await self._device.setIntensiveDuration(value)
        await self.coordinator.async_request_refresh()


class ExtraModeDuration(EasyControls3BaseEntity, TimeEntity):
    entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_extraModeDuration"
        self._attr_name = "Extra Mode Duration"

    @property
    def native_value(self) -> time | None:
        return self._device.ExtraModeDuration

    async def async_set_value(self, value: time) -> None:
        await self._device.setExtraModeDuration(value)
        await self.coordinator.async_request_refresh()


class FireplaceModeDuration(EasyControls3BaseEntity, TimeEntity):
    entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_fireplaceModeDuration"
        self._attr_name = "Individual Mode Duration"

    @property
    def native_value(self) -> time | None:
        return self._device.FireplaceModeDuration

    async def async_set_value(self, value: time) -> None:
        await self._device.setFireplaceModeDuration(value)
        await self.coordinator.async_request_refresh()
