import asyncio
import datetime
import logging
from typing import cast

from dateutil.relativedelta import relativedelta
from websockets.asyncio.client import connect

from .deviceList import deviceInfo
from .KWLStates import CellState, KWLState

LOGGER = logging.getLogger(__name__)


class EasyControls3Instance:
    def __init__(self, url: str) -> None:
        self._lock = asyncio.Lock()
        self._url: str = "ws://" + url + ":80"
        self._deviceModel: str | None = None
        self._deviceType: str | None = None
        self._SerialNR: int | None = None
        self._instanceState: KWLState | None = None
        self._CurrentFanSpeed: int | None = None
        self._intensivFanSpeed: int | None = None
        self._atHomeFanSpeed: int | None = None
        self._awayFanSpeed: int | None = None
        self._intensivDuration: datetime.time | None = None
        self._OutsideTemperature: float | None = None
        self._SupplyTemperature: float | None = None
        self._IndoorTemperature: float | None = None
        self._ExhaustTemperature: float | None = None
        self._AirRH: int | None = None
        self._filterInterval: int | None = None
        self._filterChanged: datetime.date | None = None
        self._filterDue: datetime.date | None = None
        self._isOn: bool | None = None
        # Fan RPM
        self._extractFanRPM: int | None = None
        self._supplyFanRPM: int | None = None
        # Cell / system state
        self._cellState: CellState | None = None
        self._defrosting: bool | None = None
        self._weeklyTimerEnabled: bool | None = None
        self._emergencyStopActivated: bool | None = None
        self._bypassOpen: bool | None = None
        # Uptime & filter
        self._totalUptimeYears: int | None = None
        self._totalUptimeHours: int | None = None
        self._currentUptimeHours: int | None = None
        self._filterRemainingDays: int | None = None
        # Temperature targets (read-only from device settings)
        self._homeAirTempTarget: float | None = None
        self._awayAirTempTarget: float | None = None
        self._boostAirTempTarget: float | None = None
        self._extraAirTempTarget: float | None = None
        self._fireplaceAirTempTarget: float | None = None
        # Sensor arrays (None = not present / 0xFFFF)
        self._rhSensors: list[int | None] = [None] * 6
        self._co2Sensors: list[int | None] = [None] * 6
        self._vocSensors: list[int | None] = [None] * 4
        # Extra and Fireplace mode fan speeds and durations
        self._extraTimerRemaining: int | None = None
        self._fireplaceExtractFanSpeed: int | None = None
        self._fireplaceSupplyFanSpeed: int | None = None
        self._extraExtractFanSpeed: int | None = None
        self._extraSupplyFanSpeed: int | None = None
        self._extraModeDuration: datetime.time | None = None
        self._fireplaceModeDuration: datetime.time | None = None

    def _build_write_command(self, *items: tuple[int, int]) -> bytes:
        n = len(items)
        length = n * 2 + 2
        payload = bytearray()
        payload += length.to_bytes(2, "little")
        payload += b"\xf9\x00"
        for register, value in items:
            payload += register.to_bytes(2, "little")
            payload += value.to_bytes(2, "little")
        checksum = sum(
            (payload[i * 2 + 1] << 8) + payload[i * 2]
            for i in range(len(payload) // 2)
        ) & 0xFFFF
        payload += checksum.to_bytes(2, "little")
        return bytes(payload)

    async def _exchangeData(self, request: bytes) -> bytes:
        async with self._lock, connect(self._url) as websocket:
            LOGGER.debug("connected")
            await websocket.send(request)
            LOGGER.debug("sent")
            response = await websocket.recv()
            return cast(bytes, response)

    async def readCurrentData(self) -> None:
        request = bytes.fromhex("0300f6000000f900")
        response = await self._exchangeData(request)
        self._parseData(response)

    def _parseData(self, data: bytes) -> None:
        # Binary protocol: KWL device responds with structured data at specific byte offsets.
        # Offset formula: buffer_offset = range_buffer_start + (register - range_register_start)
        # Byte access: data[buffer_offset * 2] / data[buffer_offset * 2 + 1]
        # Verified ranges: g_cyclone_hw_state (buf 63, reg 4352), g_cyclone_sw_state (buf 106, reg 4608)

        def read_word(offset: int) -> int:
            return data[offset * 2] * 256 + data[offset * 2 + 1]

        # Device identification (offsets 14-17)
        self._deviceModel = deviceInfo["device_model_data"][data[17 * 2 + 1]]
        self._deviceType = deviceInfo["device_type_data"][data[16 * 2 + 1]]
        self._SerialNR = (
            data[14 * 2] * 16777216
            + data[14 * 2 + 1] * 65536
            + data[15 * 2] * 256
            + data[15 * 2 + 1]
        )

        # Operating mode state (offsets 107, 110, 111)
        # state: A_CYC_STATE, boost: A_CYC_BOOST_TIMER, fire: A_CYC_FIREPLACE_TIMER
        # Logic: fireplace (3) > intensive/boost (2) > away (1) > at_home (0)
        state = data[107 * 2 + 1]
        fire = data[111 * 2 + 1]
        boost = data[110 * 2 + 1]
        tmpState = KWLState.AtHome
        tmpState = KWLState.Away if state != 0 else tmpState
        tmpState = KWLState.Intensive if boost != 0 else tmpState
        tmpState = KWLState.Individual if fire != 0 else tmpState
        self._instanceState = tmpState

        # Fan speeds (offsets 129, 419, 407, 431)
        self._CurrentFanSpeed = data[129]
        self._intensivFanSpeed = data[431]
        self._atHomeFanSpeed = data[419]
        self._awayFanSpeed = data[407]

        # Temperatures (offsets 65-69): raw value / 100 - 273.15 gives Celsius
        def to_celsius(offset: int) -> float:
            return round((data[offset * 2] * 256 + data[offset * 2 + 1]) / 100 - 273.15, 1)

        self._OutsideTemperature = to_celsius(67)
        self._SupplyTemperature = to_celsius(69)
        self._IndoorTemperature = to_celsius(65)
        self._ExhaustTemperature = to_celsius(66)

        # Humidity (offset 74) — A_CYC_RH_VALUE (4363)
        self._AirRH = data[74 * 2 + 1]

        # Filter status (offsets 239, 248-250)
        self._filterInterval = data[239 * 2 + 1]  # in 30-day months
        lastFilterChangedYear = 2000 + data[250 * 2 + 1]
        lastFilterChangedMonth = data[249 * 2 + 1]
        lastFilterChangedDay = data[248 * 2 + 1]
        self._filterChanged = datetime.date(
            lastFilterChangedYear, lastFilterChangedMonth, lastFilterChangedDay
        )
        self._filterDue = self._filterChanged + relativedelta(
            months=int(self._filterInterval)
        )

        # Intensive mode duration in minutes (offset 493) — A_CYC_BOOST_TIME (20544)
        intensivDurationInMinutes = data[493]
        intensivDurationHours = intensivDurationInMinutes // 60
        intensivDurationMinutes = intensivDurationInMinutes - 60 * intensivDurationHours
        self._intensivDuration = datetime.time(
            intensivDurationHours, intensivDurationMinutes
        )

        # Device power state (offset 217): 0=on, !=0=off — A_CYC_MODE (4610)
        self._isOn = bool(data[217] == 0)

        # Fan RPM — g_cyclone_hw_state (buf_start=63, reg_start=4352)
        self._extractFanRPM = read_word(72)   # A_CYC_EXTR_FAN_SPEED (4361)
        self._supplyFanRPM = read_word(73)    # A_CYC_SUPP_FAN_SPEED (4362)

        # Software state — g_cyclone_sw_state (buf_start=106, reg_start=4608)
        self._defrosting = bool(data[109 * 2 + 1])            # A_CYC_DEFROSTING (4611)
        self._extraTimerRemaining = data[112 * 2 + 1]         # A_CYC_EXTRA_TIMER (4614)
        self._weeklyTimerEnabled = bool(data[113 * 2 + 1])    # A_CYC_WEEKLY_TIMER_ENABLED (4615)
        cell_state_raw = data[114 * 2 + 1]                    # A_CYC_CELL_STATE (4616)
        self._cellState = CellState(cell_state_raw) if cell_state_raw < 4 else None
        self._totalUptimeYears = read_word(115)                # A_CYC_TOTAL_UP_TIME_YEARS (4617)
        self._totalUptimeHours = read_word(116)                # A_CYC_TOTAL_UP_TIME_HOURS (4618)
        self._currentUptimeHours = read_word(117)              # A_CYC_CURRENT_UP_TIME_HOURS (4619)
        self._filterRemainingDays = read_word(118)             # A_CYC_REMAINING_TIME_FOR_FILTER (4620)
        self._emergencyStopActivated = bool(data[122 * 2 + 1]) # A_CYC_EMERGENCY_STOP_IS_ACTIVATED (4624)

        # Output — g_cyclone_output (buf_start=138, reg_start=4864)
        self._bypassOpen = bool(data[144 * 2 + 1])            # A_CYC_IO_BYPASS (4870)

        # Settings — g_cyclone_settings (buf_start=182, reg_start=20480)
        self._fireplaceExtractFanSpeed = data[189 * 2 + 1]    # A_CYC_FIREPLACE_EXTR_FAN (20487)
        self._fireplaceSupplyFanSpeed = data[190 * 2 + 1]     # A_CYC_FIREPLACE_SUPP_FAN (20488)
        self._extraAirTempTarget = to_celsius(195)             # A_CYC_EXTRA_AIR_TEMP_TARGET (20493)
        self._extraExtractFanSpeed = data[196 * 2 + 1]        # A_CYC_EXTRA_EXTR_FAN (20494)
        self._extraSupplyFanSpeed = data[197 * 2 + 1]         # A_CYC_EXTRA_SUPP_FAN (20495)

        extra_min = data[198 * 2 + 1]                         # A_CYC_EXTRA_TIME (20496)
        self._extraModeDuration = datetime.time(extra_min // 60, extra_min % 60)

        self._fireplaceAirTempTarget = to_celsius(199)         # A_CYC_FIREPLACE_AIR_TEMP_TARGET (20497)
        self._awayAirTempTarget = to_celsius(204)              # A_CYC_AWAY_AIR_TEMP_TARGET (20502)
        self._homeAirTempTarget = to_celsius(210)              # A_CYC_HOME_AIR_TEMP_TARGET (20508)
        self._boostAirTempTarget = to_celsius(216)             # A_CYC_BOOST_AIR_TEMP_TARGET (20514)

        fp_min = data[247 * 2 + 1]                            # A_CYC_FIREPLACE_TIME (20545)
        self._fireplaceModeDuration = datetime.time(fp_min // 60, fp_min % 60)

        # RH sensors 0-5 — A_CYC_RH_SENSOR_0..5 (4373..4378), buf 84..89
        for i in range(6):
            v = read_word(84 + i)
            self._rhSensors[i] = None if v == 0xFFFF else v

        # CO2 sensors 0-5 — A_CYC_CO2_SENSOR_0..5 (4379..4384), buf 90..95
        for i in range(6):
            v = read_word(90 + i)
            self._co2Sensors[i] = None if v == 0xFFFF else v

        # VOC sensors 0-3 — A_CYC_VOC_SENSOR_0..3 (4391..4394), buf 102..105
        for i in range(4):
            v = read_word(102 + i)
            self._vocSensors[i] = None if v == 0xFFFF else v

    async def switchMode(self, wantedKWLState: KWLState) -> None:
        # Binary protocol commands for mode switching
        if wantedKWLState is KWLState.AtHome:
            requestData = "0800f9000112000004120000051200000b37"
        elif wantedKWLState is KWLState.Away:
            requestData = "0800f9000112010004120000051200000c37"
        elif wantedKWLState is KWLState.Intensive:
            duration = self._intensivDuration
            assert duration is not None
            requestedDuration = duration.hour * 60 + duration.minute
            requestData = (
                "0600f9000412"
                + (requestedDuration).to_bytes(2, byteorder="little").hex()
                + "05120000"
                + (requestedDuration + 0x2508).to_bytes(2, byteorder="little").hex()
            )
        elif wantedKWLState is KWLState.Individual:
            requestData = "0600f90004120000051296009e25"
        else:
            raise TypeError("wantedKWLState must be an instance of KWLState Enum")

        request = bytes.fromhex(requestData)
        response = await self._exchangeData(request)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("mode switch: expected response received")
        else:
            LOGGER.warning("mode switch: unexpected response from device")

    def checkFanSpeedLimit(self, requestedFanSpeed: int) -> int:
        if requestedFanSpeed < 1:
            requestedFanSpeed = 1
        elif requestedFanSpeed > 100:
            requestedFanSpeed = 100
        else:
            requestedFanSpeed = round(requestedFanSpeed)
        return requestedFanSpeed

    def createFanSpeedPlainRequestString(self, requestedFanSpeed: int) -> str:
        return f"{requestedFanSpeed:02x}"

    def createFanSpeedModdedRequestString(self, requestedFanSpeed: int, mode: KWLState) -> str:
        offset = 30  # Intensive

        if mode is KWLState.AtHome:
            offset = 24
        elif mode is KWLState.Away:
            offset = 18
        elif mode is KWLState.Intensive:
            offset = 30
        else:  # Individual/Fireplace should not be changed from here
            LOGGER.debug("Individual/Fireplace is not supported")

        return f"{requestedFanSpeed + offset:02x}"

    async def setFanSpeed(self, requestedFanSpeed: int, mode: KWLState) -> None:
        requestedFanSpeed = self.checkFanSpeedLimit(requestedFanSpeed)
        requestedSpeedPlainString = self.createFanSpeedPlainRequestString(requestedFanSpeed)
        requestedSpeedModdedString = self.createFanSpeedModdedRequestString(requestedFanSpeed, mode)

        modeIdentifier = "21"  # Intensive

        if mode is KWLState.AtHome:
            modeIdentifier = "1B"
        elif mode is KWLState.Away:
            modeIdentifier = "15"
        elif mode is KWLState.Intensive:
            modeIdentifier = "21"
        else:  # Individual/Fireplace should not be changed from here
            LOGGER.debug("Individual/Fireplace is not supported")
            return

        requestData = (
            "04 00 f9 00"
            + modeIdentifier
            + "50"
            + requestedSpeedPlainString
            + "00"
            + requestedSpeedModdedString
            + "51"
        )

        request = bytes.fromhex(requestData)
        response = await self._exchangeData(request)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("fan speed set: expected response received")
        else:
            LOGGER.warning("fan speed set: unexpected response from device")

    async def setIntensiveDuration(self, requestedDurationTime: datetime.time) -> None:
        requestedDuration = (
            requestedDurationTime.hour * 60 + requestedDurationTime.minute
        )
        if requestedDuration < 1:
            requestedDuration = 1
        elif (
            requestedDuration > 0x5A0
        ):  # if the time should be more than 0x5A0 (24*60min = 1 day it doesn't make sense anymore)
            requestedDuration = 0x5A0
        else:
            requestedDuration = round(requestedDuration)

        requestData = (
            "0400f9004050"
            + (requestedDuration).to_bytes(2, byteorder="little").hex()
            + (requestedDuration + 0x513D).to_bytes(2, byteorder="little").hex()
        )

        request = bytes.fromhex(requestData)
        response = await self._exchangeData(request)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("duration set: expected response received")
        else:
            LOGGER.warning("duration set: unexpected response from device")

    async def _setTemperatureTarget(self, register: int, celsius: float) -> None:
        value = round((celsius + 273.15) * 100)
        response = await self._exchangeData(self._build_write_command((register, value)))
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("temperature target set: expected response received")
        else:
            LOGGER.warning("temperature target set: unexpected response from device")

    async def setHomeAirTempTarget(self, celsius: float) -> None:
        await self._setTemperatureTarget(0x501C, celsius)  # A_CYC_HOME_AIR_TEMP_TARGET (20508)

    async def setAwayAirTempTarget(self, celsius: float) -> None:
        await self._setTemperatureTarget(0x5016, celsius)  # A_CYC_AWAY_AIR_TEMP_TARGET (20502)

    async def setBoostAirTempTarget(self, celsius: float) -> None:
        await self._setTemperatureTarget(0x5022, celsius)  # A_CYC_BOOST_AIR_TEMP_TARGET (20514)

    async def setExtraAirTempTarget(self, celsius: float) -> None:
        await self._setTemperatureTarget(0x500D, celsius)  # A_CYC_EXTRA_AIR_TEMP_TARGET (20493)

    async def setFireplaceAirTempTarget(self, celsius: float) -> None:
        await self._setTemperatureTarget(0x5011, celsius)  # A_CYC_FIREPLACE_AIR_TEMP_TARGET (20497)

    async def setFireplaceExtractFanSpeed(self, speed: int) -> None:
        speed = self.checkFanSpeedLimit(speed)
        response = await self._exchangeData(self._build_write_command((0x5007, speed)))  # A_CYC_FIREPLACE_EXTR_FAN (20487)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("fireplace extract fan speed set: expected response received")
        else:
            LOGGER.warning("fireplace extract fan speed set: unexpected response from device")

    async def setFireplaceSupplyFanSpeed(self, speed: int) -> None:
        speed = self.checkFanSpeedLimit(speed)
        response = await self._exchangeData(self._build_write_command((0x5008, speed)))  # A_CYC_FIREPLACE_SUPP_FAN (20488)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("fireplace supply fan speed set: expected response received")
        else:
            LOGGER.warning("fireplace supply fan speed set: unexpected response from device")

    async def setExtraExtractFanSpeed(self, speed: int) -> None:
        speed = self.checkFanSpeedLimit(speed)
        response = await self._exchangeData(self._build_write_command((0x500E, speed)))  # A_CYC_EXTRA_EXTR_FAN (20494)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("extra extract fan speed set: expected response received")
        else:
            LOGGER.warning("extra extract fan speed set: unexpected response from device")

    async def setExtraSupplyFanSpeed(self, speed: int) -> None:
        speed = self.checkFanSpeedLimit(speed)
        response = await self._exchangeData(self._build_write_command((0x500F, speed)))  # A_CYC_EXTRA_SUPP_FAN (20495)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("extra supply fan speed set: expected response received")
        else:
            LOGGER.warning("extra supply fan speed set: unexpected response from device")

    async def setExtraModeDuration(self, t: datetime.time) -> None:
        duration = max(1, min(0x5A0, t.hour * 60 + t.minute))
        response = await self._exchangeData(self._build_write_command((0x5010, duration)))  # A_CYC_EXTRA_TIME (20496)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("extra mode duration set: expected response received")
        else:
            LOGGER.warning("extra mode duration set: unexpected response from device")

    async def setFireplaceModeDuration(self, t: datetime.time) -> None:
        duration = max(1, min(0x5A0, t.hour * 60 + t.minute))
        response = await self._exchangeData(self._build_write_command((0x5041, duration)))  # A_CYC_FIREPLACE_TIME (20545)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("fireplace mode duration set: expected response received")
        else:
            LOGGER.warning("fireplace mode duration set: unexpected response from device")

    async def setWeeklyTimerEnabled(self, enabled: bool) -> None:
        response = await self._exchangeData(self._build_write_command((0x1207, int(enabled))))  # A_CYC_WEEKLY_TIMER_ENABLED (4615)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("weekly timer set: expected response received")
        else:
            LOGGER.warning("weekly timer set: unexpected response from device")

    async def test_connection(self) -> bool:
        try:
            request = bytes.fromhex("0300f6000000f900")
            response = await self._exchangeData(request)
            self._parseData(response)
            return True
        except Exception:
            return False

    async def turnOffOn(self, requestTurnOff: bool) -> None:
        if requestTurnOff is True:
            requestData = "0400f900021205000413"
        else:
            requestData = "0400f90002120000ff12"

        request = bytes.fromhex(requestData)
        response = await self._exchangeData(request)
        if bytes.fromhex("0200f500f700") == response:
            LOGGER.debug("device power: expected response received")
        else:
            LOGGER.warning("device power: unexpected response from device")

    @property
    def url(self) -> str:
        return self._url

    @property
    def deviceModel(self) -> str | None:
        return self._deviceModel

    @property
    def deviceType(self) -> str | None:
        return self._deviceType

    @property
    def serialNR(self) -> int | None:
        return self._SerialNR

    @property
    def instanceState(self) -> KWLState | None:
        return self._instanceState

    @property
    def CurrentFanSpeed(self) -> int | None:
        return self._CurrentFanSpeed

    @property
    def AtHomeFanSpeed(self) -> int | None:
        return self._atHomeFanSpeed

    @property
    def AwayFanSpeed(self) -> int | None:
        return self._awayFanSpeed

    @property
    def IntensivFanSpeed(self) -> int | None:
        return self._intensivFanSpeed

    @property
    def IntensivDuration(self) -> datetime.time | None:
        return self._intensivDuration

    @property
    def OutsideTemperature(self) -> float | None:
        return self._OutsideTemperature

    @property
    def SupplyTemperature(self) -> float | None:
        return self._SupplyTemperature

    @property
    def IndoorTemperature(self) -> float | None:
        return self._IndoorTemperature

    @property
    def ExhaustTemperature(self) -> float | None:
        return self._ExhaustTemperature

    @property
    def AirRH(self) -> int | None:
        return self._AirRH

    @property
    def filterInterval(self) -> int | None:
        return self._filterInterval

    @property
    def filterChanged(self) -> datetime.date | None:
        return self._filterChanged

    @property
    def filterDue(self) -> datetime.date | None:
        return self._filterDue

    @property
    def IsOn(self) -> bool | None:
        return self._isOn

    @property
    def ExtractFanRPM(self) -> int | None:
        return self._extractFanRPM

    @property
    def SupplyFanRPM(self) -> int | None:
        return self._supplyFanRPM

    @property
    def CellState(self) -> CellState | None:
        return self._cellState

    @property
    def Defrosting(self) -> bool | None:
        return self._defrosting

    @property
    def WeeklyTimerEnabled(self) -> bool | None:
        return self._weeklyTimerEnabled

    @property
    def EmergencyStopActivated(self) -> bool | None:
        return self._emergencyStopActivated

    @property
    def BypassOpen(self) -> bool | None:
        return self._bypassOpen

    @property
    def TotalUptimeYears(self) -> int | None:
        return self._totalUptimeYears

    @property
    def TotalUptimeHours(self) -> int | None:
        return self._totalUptimeHours

    @property
    def CurrentUptimeHours(self) -> int | None:
        return self._currentUptimeHours

    @property
    def FilterRemainingDays(self) -> int | None:
        return self._filterRemainingDays

    @property
    def HomeAirTempTarget(self) -> float | None:
        return self._homeAirTempTarget

    @property
    def AwayAirTempTarget(self) -> float | None:
        return self._awayAirTempTarget

    @property
    def BoostAirTempTarget(self) -> float | None:
        return self._boostAirTempTarget

    @property
    def ExtraAirTempTarget(self) -> float | None:
        return self._extraAirTempTarget

    @property
    def FireplaceAirTempTarget(self) -> float | None:
        return self._fireplaceAirTempTarget

    @property
    def ExtraTimerRemaining(self) -> int | None:
        return self._extraTimerRemaining

    @property
    def FireplaceExtractFanSpeed(self) -> int | None:
        return self._fireplaceExtractFanSpeed

    @property
    def FireplaceSupplyFanSpeed(self) -> int | None:
        return self._fireplaceSupplyFanSpeed

    @property
    def ExtraExtractFanSpeed(self) -> int | None:
        return self._extraExtractFanSpeed

    @property
    def ExtraSupplyFanSpeed(self) -> int | None:
        return self._extraSupplyFanSpeed

    @property
    def ExtraModeDuration(self) -> datetime.time | None:
        return self._extraModeDuration

    @property
    def FireplaceModeDuration(self) -> datetime.time | None:
        return self._fireplaceModeDuration

    def rhSensor(self, index: int) -> int | None:
        return self._rhSensors[index]

    def co2Sensor(self, index: int) -> int | None:
        return self._co2Sensors[index]

    def vocSensor(self, index: int) -> int | None:
        return self._vocSensors[index]
