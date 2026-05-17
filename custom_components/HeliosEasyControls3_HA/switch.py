from collections.abc import Awaitable, Callable

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
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
    entities: list = [
        KWLOnOffSwitch(coordinator),
        ControlSwitch(
            coordinator,
            "weeklyTimerSwitch",
            "Weekly Timer",
            lambda d: d.WeeklyTimerEnabled,
            lambda d, v: d.setWeeklyTimerEnabled(v),
            icon="mdi:calendar-clock",
        ),
        ControlSwitch(
            coordinator,
            "FilterReminderEnabled",
            "Filter Reminder",
            lambda d: d.FilterReminderEnabled,
            lambda d, v: d.setFilterReminderEnabled(v),
            icon="mdi:bell-outline",
        ),
        ControlSwitch(
            coordinator,
            "rhControlHome",
            "RH Control Home",
            lambda d: d.RhControlHome,
            lambda d, v: d.setRhControlHome(v),
        ),
        ControlSwitch(
            coordinator,
            "rhControlAway",
            "RH Control Away",
            lambda d: d.RhControlAway,
            lambda d, v: d.setRhControlAway(v),
        ),
        ControlSwitch(
            coordinator,
            "rhControlBoost",
            "RH Control Intensive",
            lambda d: d.RhControlBoost,
            lambda d, v: d.setRhControlBoost(v),
        ),
        ControlSwitch(
            coordinator,
            "bypassSetting",
            "Bypass",
            lambda d: d.BypassSetting,
            lambda d, v: d.setBypassSetting(v),
        ),
        ControlSwitch(
            coordinator,
            "steplessBypass",
            "Stepless Bypass",
            lambda d: d.SteplessBypass,
            lambda d, v: d.setSteplessBypass(v),
        ),
        ControlSwitch(
            coordinator,
            "coolHeatRecoveryEnabled",
            "Cool Recovery Enabled",
            lambda d: d.CoolHeatRecoveryEnabled,
            lambda d, v: d.setCoolHeatRecoveryEnabled(v),
        ),
        ControlSwitch(
            coordinator,
            "coolHeatRecovery",
            "Cool Recovery",
            lambda d: d.CoolHeatRecovery,
            lambda d, v: d.setCoolHeatRecovery(v),
        ),
    ]
    if coordinator.data.co2SensorCount > 0:
        entities += [
            ControlSwitch(
                coordinator,
                "co2ControlHome",
                "CO2 Control Home",
                lambda d: d.Co2ControlHome,
                lambda d, v: d.setCo2ControlHome(v),
            ),
            ControlSwitch(
                coordinator,
                "co2ControlAway",
                "CO2 Control Away",
                lambda d: d.Co2ControlAway,
                lambda d, v: d.setCo2ControlAway(v),
            ),
            ControlSwitch(
                coordinator,
                "co2ControlBoost",
                "CO2 Control Intensive",
                lambda d: d.Co2ControlBoost,
                lambda d, v: d.setCo2ControlBoost(v),
            ),
        ]
    async_add_entities(entities)


class KWLOnOffSwitch(EasyControls3BaseEntity, SwitchEntity):
    device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: EasyControls3Coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_OnOffSwitch"
        self._attr_name = "On/Off"

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
    entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name: str,
        getter: Callable[[EasyControls3Instance], bool | None],
        setter: Callable[[EasyControls3Instance, bool], Awaitable[None]],
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = name
        self._getter = getter
        self._setter = setter
        if icon is not None:
            self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        return self._getter(self._device)

    async def async_turn_on(self, **kwargs) -> None:
        await self._setter(self._device, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._setter(self._device, False)
        await self.coordinator.async_request_refresh()
