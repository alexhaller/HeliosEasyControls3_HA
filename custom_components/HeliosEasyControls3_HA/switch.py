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
    async_add_entities(
        [
            KWLOnOffSwitch(coordinator),
            WeeklyTimerSwitch(coordinator),
            FilterReminderSwitch(coordinator),
            ControlSwitch(
                coordinator,
                "rhControlHome",
                "RH Control Home",
                "RhControlHome",
                "setRhControlHome",
            ),
            ControlSwitch(
                coordinator,
                "co2ControlHome",
                "CO2 Control Home",
                "Co2ControlHome",
                "setCo2ControlHome",
            ),
            ControlSwitch(
                coordinator,
                "rhControlAway",
                "RH Control Away",
                "RhControlAway",
                "setRhControlAway",
            ),
            ControlSwitch(
                coordinator,
                "co2ControlAway",
                "CO2 Control Away",
                "Co2ControlAway",
                "setCo2ControlAway",
            ),
            ControlSwitch(
                coordinator,
                "rhControlBoost",
                "RH Control Boost",
                "RhControlBoost",
                "setRhControlBoost",
            ),
            ControlSwitch(
                coordinator,
                "co2ControlBoost",
                "CO2 Control Boost",
                "Co2ControlBoost",
                "setCo2ControlBoost",
            ),
        ]
    )


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


class ControlSwitch(EasyControls3BaseEntity, SwitchEntity):
    device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name_suffix: str,
        device_attr: str,
        setter_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = f"{self._device.deviceModel} {name_suffix}"
        self._device_attr = device_attr
        self._setter_name = setter_name

    @property
    def is_on(self) -> bool | None:
        return getattr(self._device, self._device_attr)

    async def async_turn_on(self, **kwargs) -> None:
        await getattr(self._device, self._setter_name)(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await getattr(self._device, self._setter_name)(False)
        await self.coordinator.async_request_refresh()


class FilterReminderSwitch(EasyControls3BaseEntity, SwitchEntity):
    device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_FilterReminderEnabled"
        self._attr_name = f"{self._device.deviceModel} Filter Reminder"

    @property
    def is_on(self) -> bool | None:
        return self._device.FilterReminderEnabled

    @property
    def icon(self) -> str:
        return "mdi:bell-outline"

    async def async_turn_on(self, **kwargs) -> None:
        await self._device.setFilterReminderEnabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._device.setFilterReminderEnabled(False)
        await self.coordinator.async_request_refresh()


class WeeklyTimerSwitch(EasyControls3BaseEntity, SwitchEntity):
    device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_WeeklyTimerSwitch"
        self._attr_name = f"{self._device.deviceModel} Weekly Timer"

    @property
    def is_on(self) -> bool | None:
        return self._device.WeeklyTimerEnabled

    @property
    def icon(self) -> str:
        return "mdi:calendar-clock"

    async def async_turn_on(self, **kwargs) -> None:
        await self._device.setWeeklyTimerEnabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._device.setWeeklyTimerEnabled(False)
        await self.coordinator.async_request_refresh()
