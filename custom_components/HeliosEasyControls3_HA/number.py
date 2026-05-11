from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyControls3BaseEntity, EasyControls3Coordinator
from .const import DOMAIN
from .KWLStates import KWLState


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EasyControls3Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            FanSpeedNumber(coordinator, "atHomeFanSpeed", "Fan Speed At Home", "AtHomeFanSpeed", KWLState.AtHome),
            FanSpeedNumber(coordinator, "awayFanSpeed", "Fan Speed Away", "AwayFanSpeed", KWLState.Away),
            FanSpeedNumber(coordinator, "intensivFanSpeed", "Fan Speed Intensive", "IntensivFanSpeed", KWLState.Intensive),
            ModeFanSpeedNumber(coordinator, "fireplaceExtractFanSpeed", "Fireplace Extract Fan Speed", "FireplaceExtractFanSpeed", "setFireplaceExtractFanSpeed"),
            ModeFanSpeedNumber(coordinator, "fireplaceSupplyFanSpeed", "Fireplace Supply Fan Speed", "FireplaceSupplyFanSpeed", "setFireplaceSupplyFanSpeed"),
            ModeFanSpeedNumber(coordinator, "extraExtractFanSpeed", "Extra Extract Fan Speed", "ExtraExtractFanSpeed", "setExtraExtractFanSpeed"),
            ModeFanSpeedNumber(coordinator, "extraSupplyFanSpeed", "Extra Supply Fan Speed", "ExtraSupplyFanSpeed", "setExtraSupplyFanSpeed"),
            AirTempTargetNumber(coordinator, "homeAirTempTarget", "Home Air Temp Target", "HomeAirTempTarget", "setHomeAirTempTarget"),
            AirTempTargetNumber(coordinator, "awayAirTempTarget", "Away Air Temp Target", "AwayAirTempTarget", "setAwayAirTempTarget"),
            AirTempTargetNumber(coordinator, "boostAirTempTarget", "Boost Air Temp Target", "BoostAirTempTarget", "setBoostAirTempTarget"),
            AirTempTargetNumber(coordinator, "extraAirTempTarget", "Extra Air Temp Target", "ExtraAirTempTarget", "setExtraAirTempTarget"),
            AirTempTargetNumber(coordinator, "fireplaceAirTempTarget", "Fireplace Air Temp Target", "FireplaceAirTempTarget", "setFireplaceAirTempTarget"),
        ]
    )


class FanSpeedNumber(EasyControls3BaseEntity, NumberEntity):
    native_min_value = 1.0
    native_max_value = 100.0
    native_step = 1.0
    native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: EasyControls3Coordinator,
        unique_suffix: str,
        name_suffix: str,
        device_attr: str,
        mode: KWLState,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device.serialNR}_{unique_suffix}"
        self._attr_name = f"{self._device.deviceModel} {name_suffix}"
        self._device_attr = device_attr
        self._mode = mode

    @property
    def icon(self) -> str:
        return "mdi:fan"

    @property
    def native_value(self):
        return getattr(self._device, self._device_attr)

    async def async_set_native_value(self, value: float) -> None:
        await self._device.setFanSpeed(int(value), self._mode)
        await self.coordinator.async_request_refresh()


class ModeFanSpeedNumber(EasyControls3BaseEntity, NumberEntity):
    native_min_value = 1.0
    native_max_value = 100.0
    native_step = 1.0
    native_unit_of_measurement = PERCENTAGE

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
    def icon(self) -> str:
        return "mdi:fan"

    @property
    def native_value(self):
        return getattr(self._device, self._device_attr)

    async def async_set_native_value(self, value: float) -> None:
        await getattr(self._device, self._setter_name)(int(value))
        await self.coordinator.async_request_refresh()


class AirTempTargetNumber(EasyControls3BaseEntity, NumberEntity):
    device_class = NumberDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    native_min_value = -10.0
    native_max_value = 40.0
    native_step = 1.0

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
    def native_value(self):
        return getattr(self._device, self._device_attr)

    async def async_set_native_value(self, value: float) -> None:
        await getattr(self._device, self._setter_name)(value)
        await self.coordinator.async_request_refresh()
