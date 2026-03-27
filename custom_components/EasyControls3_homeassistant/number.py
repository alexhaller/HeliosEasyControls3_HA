from datetime import timedelta

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup number entities."""
    easyConnector = hass.data[DOMAIN][config_entry.entry_id]

    if easyConnector.serialNR is None:
        await easyConnector.readCurrentData()

    async_add_entities(
        [
            FanSpeedNumberAtHome(easyConnector),
            FanSpeedNumberAway(easyConnector),
            FanSpeedNumberIntensive(easyConnector),
        ]
    )


class FanSpeedNumber(NumberEntity):
    """Base fan speed number entity."""

    device_class = NumberDeviceClass.POWER_FACTOR
    native_step = 1.0

    def __init__(self, easyConnector: object) -> None:
        """Initialize the number entity."""
        self._easyConnector = easyConnector

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._easyConnector.serialNR)}}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._easyConnector.IsAvailable

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Set Speed for intensive Fan"


class FanSpeedNumberAtHome(FanSpeedNumber):
    """Fan speed number entity for at-home mode."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the number entity."""
        super().__init__(easyConnector)
        self._attr_unique_id = f"{self._easyConnector.serialNR}_atHomeFanSpeed"
        self._attr_name = (
            f"{self._easyConnector.deviceModel} Fan Speed for at home mode"
        )
        self.native_value = self._easyConnector.AtHomeFanSpeed

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Set fan speed for at home mode"

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.native_value = value
        await self._easyConnector.setAtHomeFanSpeed(value)

    async def async_update(self) -> None:
        """Update the fan speed value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.AtHomeFanSpeed


class FanSpeedNumberAway(FanSpeedNumber):
    """Fan speed number entity for away mode."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the number entity."""
        super().__init__(easyConnector)
        self._attr_unique_id = f"{self._easyConnector.serialNR}_awayFanSpeed"
        self._attr_name = f"{self._easyConnector.deviceModel} Fan Speed for away mode"
        self.native_value = self._easyConnector.AwayFanSpeed

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Set fan speed for away mode"

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.native_value = value
        await self._easyConnector.setAwayFanSpeed(value)

    async def async_update(self) -> None:
        """Update the fan speed value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.AwayFanSpeed


class FanSpeedNumberIntensive(FanSpeedNumber):
    """Fan speed number entity for intensive mode."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the number entity."""
        super().__init__(easyConnector)
        self._attr_unique_id = f"{self._easyConnector.serialNR}_intensivFanSpeed"
        self._attr_name = f"{self._easyConnector.deviceModel} Fan Speed for intensive"
        self.native_value = self._easyConnector.IntensivFanSpeed

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return "Set fan speed for intensive mode"

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.native_value = value
        await self._easyConnector.setIntensiveFanSpeed(value)

    async def async_update(self) -> None:
        """Update the fan speed value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.IntensivFanSpeed
