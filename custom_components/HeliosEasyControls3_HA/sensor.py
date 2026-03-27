from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    CONCENTRATION_PARTS_PER_MILLION,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    easyConnector = hass.data[DOMAIN][config_entry.entry_id]

    if easyConnector.serialNR is None:
        await easyConnector.readCurrentData()

    new_devices = []

    new_devices.append(HumiditySensor(easyConnector))
    new_devices.append(OutsideTemperatureSensor(easyConnector))
    new_devices.append(SupplyTemperatureSensor(easyConnector))
    new_devices.append(IndoorTemperatureSensor(easyConnector))
    new_devices.append(ExhaustTemperatureSensor(easyConnector))
    new_devices.append(CurrentFanSpeed(easyConnector))
    new_devices.append(FilterChanged(easyConnector))
    new_devices.append(FilterDue(easyConnector))

    if easyConnector.CO2Value != 0xFFFF:  # only add CO2 sensor if it is available
        new_devices.append(CO2Sensor(easyConnector))

    if new_devices:
        async_add_entities(new_devices)


class SensorBase(SensorEntity):
    """Base representation of a Sensor."""

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        self._easyConnector = easyConnector

    @property
    def device_info(self) -> dict:
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, self._easyConnector.serialNR)}}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._easyConnector.IsAvailable


class HumiditySensor(SensorBase):
    """Humidity sensor representation."""

    device_class = SensorDeviceClass.HUMIDITY

    native_unit_of_measurement = PERCENTAGE
    unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_AirRH"
        self._attr_name = f"{self._easyConnector.deviceModel} Air Relativ Humidity"

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        return self._easyConnector.AirRH

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.AirRH


class OutsideTemperatureSensor(SensorBase):
    """Outside temperature sensor representation."""

    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_OutsideTemperature"
        self._attr_name = f"{self._easyConnector.deviceModel} Outside Temperature"

    @property
    def state(self) -> float | None:
        """Return the state of the sensor."""
        return self._easyConnector.OutsideTemperature

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.OutsideTemperature


class SupplyTemperatureSensor(SensorBase):
    """Supply temperature sensor representation."""

    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_SupplyTemperature"
        self._attr_name = f"{self._easyConnector.deviceModel} Supply Temperature"

    @property
    def state(self) -> float | None:
        """Return the state of the sensor."""
        return self._easyConnector.SupplyTemperature

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.SupplyTemperature


class IndoorTemperatureSensor(SensorBase):
    """Indoor temperature sensor representation."""

    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_IndoorTemperature"
        self._attr_name = f"{self._easyConnector.deviceModel} Indoor Temperature"

    @property
    def state(self) -> float | None:
        """Return the state of the sensor."""
        return self._easyConnector.IndoorTemperature

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.IndoorTemperature


class ExhaustTemperatureSensor(SensorBase):
    """Exhaust temperature sensor representation."""

    device_class = SensorDeviceClass.TEMPERATURE
    native_unit_of_measurement = UnitOfTemperature.CELSIUS
    unit_of_measurement = UnitOfTemperature.CELSIUS
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)
        self._attr_unique_id = f"{self._easyConnector.serialNR}_ExhaustTemperature"
        self._attr_name = f"{self._easyConnector.deviceModel} Exhaust Temperature"

    @property
    def state(self) -> float | None:
        """Return the state of the sensor."""
        return self._easyConnector.ExhaustTemperature

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.ExhaustTemperature


class CO2Sensor(SensorBase):
    """CO2 sensor representation."""

    device_class = SensorDeviceClass.CO2
    native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)
        self._attr_unique_id = f"{self._easyConnector.serialNR}_CO2Value"
        self._attr_name = f"{self._easyConnector.deviceModel} CO2 Value"

    @property
    def state(self) -> int:
        """Return the state of the sensor."""
        if self._easyConnector.CO2Value == 0xFFFF:
            return 0
        return self._easyConnector.CO2Value

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        if self._easyConnector.CO2Value == 0xFFFF:
            self.native_value = 0
        else:
            self.native_value = self._easyConnector.CO2Value

    @property
    def available(self) -> bool:
        """Return True if sensor is available."""
        return (
            self._easyConnector.IsAvailable and self._easyConnector.CO2Value != 0xFFFF
        )


class CurrentFanSpeed(SensorBase):
    """Current fan speed sensor representation."""

    device_class = SensorDeviceClass.POWER_FACTOR

    native_unit_of_measurement = PERCENTAGE
    unit_of_measurement = PERCENTAGE
    state_class = SensorStateClass.MEASUREMENT
    suggested_display_precision = 1

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_CurrentFanSpeed"
        self._attr_name = f"{self._easyConnector.deviceModel} current Fan Speed"

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        return self._easyConnector.CurrentFanSpeed

    @property
    def icon(self) -> str:
        """Return icon for fan."""
        return "mdi:fan"

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.CurrentFanSpeed


class FilterChanged(SensorBase):
    """Last filter change date sensor representation."""

    device_class = SensorDeviceClass.DATE

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_filterChanged"
        self._attr_name = f"{self._easyConnector.deviceModel} last filter change"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._easyConnector.filterChanged

    @property
    def icon(self) -> str:
        """Return calendar icon."""
        return "mdi:calendar-sync-outline"

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.filterChanged


class FilterDue(SensorBase):
    """Next filter change date sensor representation."""

    device_class = SensorDeviceClass.DATE

    def __init__(self, easyConnector: object) -> None:
        """Initialize the sensor."""
        super().__init__(easyConnector)

        self._attr_unique_id = f"{self._easyConnector.serialNR}_filterDue"
        self._attr_name = f"{self._easyConnector.deviceModel} next filter change"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._easyConnector.filterDue

    @property
    def icon(self) -> str:
        """Return calendar alert icon."""
        return "mdi:calendar-alert-outline"

    async def async_update(self) -> None:
        """Update sensor value."""
        await self._easyConnector.readCurrentData()
        self.native_value = self._easyConnector.filterDue
