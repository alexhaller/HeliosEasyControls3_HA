import asyncio
import datetime
import logging
from typing import cast

from dateutil.relativedelta import relativedelta
from websockets.asyncio.client import connect

from .deviceList import deviceInfo
from .KWLStates import CellState, KWLState

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Read buffer offsets  (byte index = offset * 2 / offset * 2 + 1)
# formula: buf_offset = range_buf_start + (register - range_reg_start)
# ---------------------------------------------------------------------------

# General info (buf = reg)
_BUF_SERIAL_MSW = 14
_BUF_SERIAL_LSW = 15
_BUF_MACHINE_TYPE = 16
_BUF_MACHINE_MODEL = 17

# Hardware state (buf_start=63, reg_start=4352)
_BUF_FAN_SPEED = 64
_BUF_TEMP_EXTRACT = 65
_BUF_TEMP_EXHAUST = 66
_BUF_TEMP_OUTDOOR = 67
_BUF_TEMP_SUPPLY = 69
_BUF_EXTR_FAN_RPM = 72
_BUF_SUPP_FAN_RPM = 73
_BUF_RH_VALUE = 74
_BUF_RH_SENSOR_0 = 84  # ..89
_BUF_CO2_SENSOR_0 = 90  # ..95
_BUF_VOC_SENSOR_0 = 102  # ..105

# Software state (buf_start=106, reg_start=4608)
_BUF_STATE = 107
_BUF_MODE = 108
_BUF_DEFROSTING = 109
_BUF_BOOST_TIMER = 110
_BUF_FIREPLACE_TIMER = 111
_BUF_EXTRA_TIMER = 112
_BUF_WEEKLY_TIMER = 113
_BUF_CELL_STATE = 114
_BUF_UPTIME_YEARS = 115
_BUF_UPTIME_HOURS = 116
_BUF_CURRENT_UPTIME = 117
_BUF_FILTER_REMAINING = 118
_BUF_EMERGENCY_STOP = 122

# Output (buf_start=138, reg_start=4864)
_BUF_IO_BYPASS = 144

# Settings (buf_start=182, reg_start=20480)
_BUF_SUPPLY_HEATING_MODE = 183
_BUF_FIREPLACE_EXTR_FAN = 189
_BUF_FIREPLACE_SUPP_FAN = 190
_BUF_EXTRA_AIR_TEMP = 195
_BUF_EXTRA_EXTR_FAN = 196
_BUF_EXTRA_SUPP_FAN = 197
_BUF_EXTRA_TIME = 198
_BUF_FIREPLACE_AIR_TEMP = 199
_BUF_RH_CTRL_HOME = 201  # ⚠️ label may be swapped with Away
_BUF_CO2_CTRL_HOME = 202  # ⚠️ label may be swapped with Away
_BUF_AWAY_SPEED = 203
_BUF_AWAY_AIR_TEMP = 204
_BUF_FILTER_REMINDER_DIS = 205  # inverted: 1 = reminder disabled
_BUF_RH_CTRL_AWAY = 207  # ⚠️ label may be swapped with Home
_BUF_CO2_CTRL_AWAY = 208  # ⚠️ label may be swapped with Home
_BUF_HOME_SPEED = 209
_BUF_HOME_AIR_TEMP = 210
_BUF_BOOST_RH_CTRL = 213
_BUF_BOOST_CO2_CTRL = 214
_BUF_BOOST_SPEED = 215
_BUF_BOOST_AIR_TEMP = 216
_BUF_COOL_HEAT_REC_EN = 219
_BUF_COOL_HEAT_REC = 220
_BUF_HEAT_EXCHANGER = 222
_BUF_MAX_CO2 = 223
_BUF_MAX_RH = 225
_BUF_STEPLESS_BYPASS = 227
_BUF_BYPASS_SETTING = 230
_BUF_BOOST_DURATION = 246
_BUF_FIREPLACE_DURATION = 247
_BUF_FILTER_INTERVAL = 239
_BUF_FILTER_CHANGED_DAY = 248
_BUF_FILTER_CHANGED_MONTH = 249
_BUF_FILTER_CHANGED_YEAR = 250

# ---------------------------------------------------------------------------
# Write register addresses
# ---------------------------------------------------------------------------
_REG_STATE = 0x1201
_REG_MODE = 0x1202
_REG_BOOST_TIMER = 0x1204
_REG_FIREPLACE_TIMER = 0x1205
_REG_WEEKLY_TIMER = 0x1207
_REG_SUPPLY_HEATING = 0x5001
_REG_FIREPLACE_EXTR_FAN = 0x5007
_REG_FIREPLACE_SUPP_FAN = 0x5008
_REG_EXTRA_AIR_TEMP = 0x500D
_REG_EXTRA_EXTR_FAN = 0x500E
_REG_EXTRA_SUPP_FAN = 0x500F
_REG_EXTRA_TIME = 0x5010
_REG_FIREPLACE_AIR_TEMP = 0x5011
_REG_RH_CTRL_HOME = 0x5013
_REG_CO2_CTRL_HOME = 0x5014
_REG_AWAY_FAN_SPEED = 0x5015
_REG_AWAY_AIR_TEMP = 0x5016
_REG_FILTER_REMINDER = 0x5017
_REG_RH_CTRL_AWAY = 0x5019
_REG_CO2_CTRL_AWAY = 0x501A
_REG_HOME_FAN_SPEED = 0x501B
_REG_HOME_AIR_TEMP = 0x501C
_REG_BOOST_RH_CTRL = 0x501F
_REG_BOOST_CO2_CTRL = 0x5020
_REG_BOOST_FAN_SPEED = 0x5021
_REG_BOOST_AIR_TEMP = 0x5022
_REG_COOL_HEAT_REC_EN = 0x5025
_REG_COOL_HEAT_REC = 0x5026
_REG_HEAT_EXCHANGER = 0x5028
_REG_MAX_CO2 = 0x5029
_REG_MAX_RH = 0x502B
_REG_STEPLESS_BYPASS = 0x502D
_REG_BYPASS_SETTING = 0x5030
_REG_BOOST_DURATION = 0x5040
_REG_FIREPLACE_DURATION = 0x5041

_FAN_SPEED_REG: dict[KWLState, int] = {
    KWLState.AtHome: _REG_HOME_FAN_SPEED,
    KWLState.Away: _REG_AWAY_FAN_SPEED,
    KWLState.Intensive: _REG_BOOST_FAN_SPEED,
}

_READ_REQUEST = bytes.fromhex("0300f6000000f900")
_WRITE_OK = bytes.fromhex("0200f500f700")

# ---------------------------------------------------------------------------
# Frame parsing helpers
# ---------------------------------------------------------------------------


def _word(data: bytes, offset: int) -> int:
    return data[offset * 2] * 256 + data[offset * 2 + 1]


def _low(data: bytes, offset: int) -> int:
    return data[offset * 2 + 1]


def _kelvin_word_to_celsius(data: bytes, offset: int) -> float:
    return round(_word(data, offset) / 100 - 273.15, 1)


def _minutes_to_time(minutes: int) -> datetime.time:
    return datetime.time(minutes // 60, minutes % 60)


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
        self._extractFanRPM: int | None = None
        self._supplyFanRPM: int | None = None
        self._cellState: CellState | None = None
        self._defrosting: bool | None = None
        self._weeklyTimerEnabled: bool | None = None
        self._emergencyStopActivated: bool | None = None
        self._bypassOpen: bool | None = None
        self._totalUptimeYears: int | None = None
        self._totalUptimeHours: int | None = None
        self._currentUptimeHours: int | None = None
        self._filterRemainingDays: int | None = None
        self._homeAirTempTarget: float | None = None
        self._awayAirTempTarget: float | None = None
        self._boostAirTempTarget: float | None = None
        self._extraAirTempTarget: float | None = None
        self._fireplaceAirTempTarget: float | None = None
        self._rhSensors: list[int | None] = [None] * 6
        self._co2Sensors: list[int | None] = [None] * 6
        self._vocSensors: list[int | None] = [None] * 4
        self._boostTimerRemaining: int | None = None
        self._fireplaceTimerRemaining: int | None = None
        self._rhControlHome: bool | None = None
        self._co2ControlHome: bool | None = None
        self._rhControlAway: bool | None = None
        self._co2ControlAway: bool | None = None
        self._rhControlBoost: bool | None = None
        self._co2ControlBoost: bool | None = None
        self._filterReminderEnabled: bool | None = None
        self._extraTimerRemaining: int | None = None
        self._fireplaceExtractFanSpeed: int | None = None
        self._fireplaceSupplyFanSpeed: int | None = None
        self._extraExtractFanSpeed: int | None = None
        self._extraSupplyFanSpeed: int | None = None
        self._extraModeDuration: datetime.time | None = None
        self._fireplaceModeDuration: datetime.time | None = None
        self._supplyHeatingAdjustMode: int | None = None
        self._maxRH: int | None = None
        self._maxCO2: int | None = None
        self._bypassSetting: bool | None = None
        self._steplessBypass: bool | None = None
        self._coolHeatRecoveryEnabled: bool | None = None
        self._coolHeatRecovery: bool | None = None
        self._heatExchanger: int | None = None

    # ---------------------------------------------------------------------------
    # Protocol helpers
    # ---------------------------------------------------------------------------

    def _build_write_command(self, *items: tuple[int, int]) -> bytes:
        n = len(items)
        payload = bytearray()
        payload += (n * 2 + 2).to_bytes(2, "little")
        payload += b"\xf9\x00"
        for register, value in items:
            payload += register.to_bytes(2, "little")
            payload += value.to_bytes(2, "little")
        checksum = (
            sum(
                (payload[i * 2 + 1] << 8) + payload[i * 2]
                for i in range(len(payload) // 2)
            )
            & 0xFFFF
        )
        payload += checksum.to_bytes(2, "little")
        return bytes(payload)

    def _check_write_response(self, response: bytes, context: str) -> None:
        if response == _WRITE_OK:
            LOGGER.debug("%s: write acknowledged", context)
        else:
            LOGGER.warning("%s: unexpected response from device", context)

    async def _exchangeData(self, request: bytes) -> bytes:
        async with self._lock, connect(self._url) as websocket:
            LOGGER.debug("connected")
            await websocket.send(request)
            LOGGER.debug("sent")
            response = await websocket.recv()
            return cast(bytes, response)

    # ---------------------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------------------

    async def readCurrentData(self) -> None:
        response = await self._exchangeData(_READ_REQUEST)
        self._parseData(response)

    def _parseData(self, data: bytes) -> None:
        self._parse_device_info(data)
        self._parse_hw_state(data)
        self._parse_sw_state(data)
        self._parse_output(data)
        self._parse_settings(data)

    def _parse_device_info(self, data: bytes) -> None:
        self._deviceModel = deviceInfo["device_model_data"][
            _low(data, _BUF_MACHINE_MODEL)
        ]
        self._deviceType = deviceInfo["device_type_data"][_low(data, _BUF_MACHINE_TYPE)]
        self._SerialNR = _word(data, _BUF_SERIAL_MSW) * 65536 + _word(
            data, _BUF_SERIAL_LSW
        )

    def _parse_hw_state(self, data: bytes) -> None:
        self._CurrentFanSpeed = _low(data, _BUF_FAN_SPEED)
        self._OutsideTemperature = _kelvin_word_to_celsius(data, _BUF_TEMP_OUTDOOR)
        self._SupplyTemperature = _kelvin_word_to_celsius(data, _BUF_TEMP_SUPPLY)
        self._IndoorTemperature = _kelvin_word_to_celsius(data, _BUF_TEMP_EXTRACT)
        self._ExhaustTemperature = _kelvin_word_to_celsius(data, _BUF_TEMP_EXHAUST)
        self._extractFanRPM = _word(data, _BUF_EXTR_FAN_RPM)
        self._supplyFanRPM = _word(data, _BUF_SUPP_FAN_RPM)
        self._AirRH = _low(data, _BUF_RH_VALUE)
        for i in range(6):
            v = _word(data, _BUF_RH_SENSOR_0 + i)
            self._rhSensors[i] = None if v == 0xFFFF else v
        for i in range(6):
            v = _word(data, _BUF_CO2_SENSOR_0 + i)
            self._co2Sensors[i] = None if v == 0xFFFF else v
        for i in range(4):
            v = _word(data, _BUF_VOC_SENSOR_0 + i)
            self._vocSensors[i] = None if v == 0xFFFF or v == 0 else v

    def _parse_sw_state(self, data: bytes) -> None:
        state = _low(data, _BUF_STATE)
        boost = _word(data, _BUF_BOOST_TIMER)
        fire = _word(data, _BUF_FIREPLACE_TIMER)
        if fire:
            self._instanceState = KWLState.Individual
        elif boost:
            self._instanceState = KWLState.Intensive
        elif state:
            self._instanceState = KWLState.Away
        else:
            self._instanceState = KWLState.AtHome
        self._isOn = _low(data, _BUF_MODE) == 0
        self._defrosting = bool(_low(data, _BUF_DEFROSTING))
        self._boostTimerRemaining = boost
        self._fireplaceTimerRemaining = fire
        self._extraTimerRemaining = _word(data, _BUF_EXTRA_TIMER)
        self._weeklyTimerEnabled = bool(_low(data, _BUF_WEEKLY_TIMER))
        cell_raw = _low(data, _BUF_CELL_STATE)
        self._cellState = CellState(cell_raw) if cell_raw < 4 else None
        self._totalUptimeYears = _word(data, _BUF_UPTIME_YEARS)
        self._totalUptimeHours = _word(data, _BUF_UPTIME_HOURS)
        self._currentUptimeHours = _word(data, _BUF_CURRENT_UPTIME)
        self._filterRemainingDays = _word(data, _BUF_FILTER_REMAINING)
        self._emergencyStopActivated = bool(_low(data, _BUF_EMERGENCY_STOP))

    def _parse_output(self, data: bytes) -> None:
        self._bypassOpen = bool(_low(data, _BUF_IO_BYPASS))

    def _parse_settings(self, data: bytes) -> None:
        self._supplyHeatingAdjustMode = _low(data, _BUF_SUPPLY_HEATING_MODE)
        self._fireplaceExtractFanSpeed = _low(data, _BUF_FIREPLACE_EXTR_FAN)
        self._fireplaceSupplyFanSpeed = _low(data, _BUF_FIREPLACE_SUPP_FAN)
        self._extraAirTempTarget = _kelvin_word_to_celsius(data, _BUF_EXTRA_AIR_TEMP)
        self._extraExtractFanSpeed = _low(data, _BUF_EXTRA_EXTR_FAN)
        self._extraSupplyFanSpeed = _low(data, _BUF_EXTRA_SUPP_FAN)
        self._extraModeDuration = _minutes_to_time(_word(data, _BUF_EXTRA_TIME))
        self._fireplaceAirTempTarget = _kelvin_word_to_celsius(
            data, _BUF_FIREPLACE_AIR_TEMP
        )
        self._rhControlHome = bool(_low(data, _BUF_RH_CTRL_HOME))
        self._co2ControlHome = bool(_low(data, _BUF_CO2_CTRL_HOME))
        self._awayAirTempTarget = _kelvin_word_to_celsius(data, _BUF_AWAY_AIR_TEMP)
        self._filterReminderEnabled = not bool(_low(data, _BUF_FILTER_REMINDER_DIS))
        self._rhControlAway = bool(_low(data, _BUF_RH_CTRL_AWAY))
        self._co2ControlAway = bool(_low(data, _BUF_CO2_CTRL_AWAY))
        self._homeAirTempTarget = _kelvin_word_to_celsius(data, _BUF_HOME_AIR_TEMP)
        self._rhControlBoost = bool(_low(data, _BUF_BOOST_RH_CTRL))
        self._co2ControlBoost = bool(_low(data, _BUF_BOOST_CO2_CTRL))
        self._boostAirTempTarget = _kelvin_word_to_celsius(data, _BUF_BOOST_AIR_TEMP)
        self._coolHeatRecoveryEnabled = bool(_low(data, _BUF_COOL_HEAT_REC_EN))
        self._coolHeatRecovery = bool(_low(data, _BUF_COOL_HEAT_REC))
        self._heatExchanger = _low(data, _BUF_HEAT_EXCHANGER)
        self._maxCO2 = _word(data, _BUF_MAX_CO2)
        self._maxRH = _low(data, _BUF_MAX_RH)
        LOGGER.warning(
            "DEBUG settings buffer offsets 182-260: %s",
            "  ".join(
                f"[{i}]=0x{data[i * 2]:02X}{data[i * 2 + 1]:02X}"
                for i in range(182, 261)
            ),
        )
        self._steplessBypass = bool(_low(data, _BUF_STEPLESS_BYPASS))
        self._bypassSetting = bool(_low(data, _BUF_BYPASS_SETTING))
        self._intensivDuration = _minutes_to_time(_word(data, _BUF_BOOST_DURATION))
        self._fireplaceModeDuration = _minutes_to_time(
            _word(data, _BUF_FIREPLACE_DURATION)
        )
        self._filterInterval = _low(data, _BUF_FILTER_INTERVAL)
        day = _low(data, _BUF_FILTER_CHANGED_DAY)
        month = _low(data, _BUF_FILTER_CHANGED_MONTH)
        year = 2000 + _low(data, _BUF_FILTER_CHANGED_YEAR)
        self._filterChanged = datetime.date(year, month, day)
        self._filterDue = self._filterChanged + relativedelta(
            months=int(self._filterInterval)
        )
        self._atHomeFanSpeed = _low(data, _BUF_HOME_SPEED)
        self._awayFanSpeed = _low(data, _BUF_AWAY_SPEED)
        self._intensivFanSpeed = _low(data, _BUF_BOOST_SPEED)

    # ---------------------------------------------------------------------------
    # Write — mode and power
    # ---------------------------------------------------------------------------

    async def switchMode(self, wantedKWLState: KWLState) -> None:
        if wantedKWLState is KWLState.AtHome:
            cmd = self._build_write_command(
                (_REG_STATE, 0), (_REG_BOOST_TIMER, 0), (_REG_FIREPLACE_TIMER, 0)
            )
        elif wantedKWLState is KWLState.Away:
            cmd = self._build_write_command(
                (_REG_STATE, 1), (_REG_BOOST_TIMER, 0), (_REG_FIREPLACE_TIMER, 0)
            )
        elif wantedKWLState is KWLState.Intensive:
            assert self._intensivDuration is not None
            duration = self._intensivDuration.hour * 60 + self._intensivDuration.minute
            cmd = self._build_write_command(
                (_REG_BOOST_TIMER, duration), (_REG_FIREPLACE_TIMER, 0)
            )
        elif wantedKWLState is KWLState.Individual:
            cmd = self._build_write_command(
                (_REG_BOOST_TIMER, 0), (_REG_FIREPLACE_TIMER, 0x96)
            )
        else:
            raise TypeError("wantedKWLState must be an instance of KWLState Enum")
        response = await self._exchangeData(cmd)
        self._check_write_response(response, "mode switch")

    async def turnOffOn(self, requestTurnOff: bool) -> None:
        response = await self._exchangeData(
            self._build_write_command((_REG_MODE, 5 if requestTurnOff else 0))
        )
        self._check_write_response(response, "device power")

    # ---------------------------------------------------------------------------
    # Write — fan speed
    # ---------------------------------------------------------------------------

    def checkFanSpeedLimit(self, requestedFanSpeed: int) -> int:
        return max(1, min(100, round(requestedFanSpeed)))

    async def setFanSpeed(self, requestedFanSpeed: int, mode: KWLState) -> None:
        if mode not in _FAN_SPEED_REG:
            LOGGER.debug("setFanSpeed: Individual mode is not supported")
            return
        response = await self._exchangeData(
            self._build_write_command(
                (_FAN_SPEED_REG[mode], self.checkFanSpeedLimit(requestedFanSpeed))
            )
        )
        self._check_write_response(response, "fan speed set")

    async def setIntensiveDuration(self, requestedDurationTime: datetime.time) -> None:
        duration = max(
            1,
            min(0x5A0, requestedDurationTime.hour * 60 + requestedDurationTime.minute),
        )
        response = await self._exchangeData(
            self._build_write_command((_REG_BOOST_DURATION, duration))
        )
        self._check_write_response(response, "intensive duration set")

    # ---------------------------------------------------------------------------
    # Write — settings
    # ---------------------------------------------------------------------------

    async def _set_temperature(self, register: int, celsius: float) -> None:
        response = await self._exchangeData(
            self._build_write_command((register, round((celsius + 273.15) * 100)))
        )
        self._check_write_response(response, "temperature target set")

    async def _set_flag(self, register: int, enabled: bool) -> None:
        response = await self._exchangeData(
            self._build_write_command((register, int(enabled)))
        )
        self._check_write_response(response, "flag set")

    async def _set_int(self, register: int, value: int) -> None:
        response = await self._exchangeData(
            self._build_write_command((register, value))
        )
        self._check_write_response(response, "value set")

    async def setHomeAirTempTarget(self, celsius: float) -> None:
        await self._set_temperature(_REG_HOME_AIR_TEMP, celsius)

    async def setAwayAirTempTarget(self, celsius: float) -> None:
        await self._set_temperature(_REG_AWAY_AIR_TEMP, celsius)

    async def setBoostAirTempTarget(self, celsius: float) -> None:
        await self._set_temperature(_REG_BOOST_AIR_TEMP, celsius)

    async def setExtraAirTempTarget(self, celsius: float) -> None:
        await self._set_temperature(_REG_EXTRA_AIR_TEMP, celsius)

    async def setFireplaceAirTempTarget(self, celsius: float) -> None:
        await self._set_temperature(_REG_FIREPLACE_AIR_TEMP, celsius)

    async def setFireplaceExtractFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_FIREPLACE_EXTR_FAN, self.checkFanSpeedLimit(speed))

    async def setFireplaceSupplyFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_FIREPLACE_SUPP_FAN, self.checkFanSpeedLimit(speed))

    async def setExtraExtractFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_EXTRA_EXTR_FAN, self.checkFanSpeedLimit(speed))

    async def setExtraSupplyFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_EXTRA_SUPP_FAN, self.checkFanSpeedLimit(speed))

    async def setExtraModeDuration(self, t: datetime.time) -> None:
        await self._set_int(_REG_EXTRA_TIME, max(1, min(0x5A0, t.hour * 60 + t.minute)))

    async def setFireplaceModeDuration(self, t: datetime.time) -> None:
        await self._set_int(
            _REG_FIREPLACE_DURATION, max(1, min(0x5A0, t.hour * 60 + t.minute))
        )

    async def setWeeklyTimerEnabled(self, enabled: bool) -> None:
        await self._set_flag(_REG_WEEKLY_TIMER, enabled)

    async def setRhControlHome(self, enabled: bool) -> None:
        await self._set_flag(_REG_RH_CTRL_HOME, enabled)

    async def setCo2ControlHome(self, enabled: bool) -> None:
        await self._set_flag(_REG_CO2_CTRL_HOME, enabled)

    async def setRhControlAway(self, enabled: bool) -> None:
        await self._set_flag(_REG_RH_CTRL_AWAY, enabled)

    async def setCo2ControlAway(self, enabled: bool) -> None:
        await self._set_flag(_REG_CO2_CTRL_AWAY, enabled)

    async def setRhControlBoost(self, enabled: bool) -> None:
        await self._set_flag(_REG_BOOST_RH_CTRL, enabled)

    async def setCo2ControlBoost(self, enabled: bool) -> None:
        await self._set_flag(_REG_BOOST_CO2_CTRL, enabled)

    async def setFilterReminderEnabled(self, enabled: bool) -> None:
        await self._set_flag(_REG_FILTER_REMINDER, not enabled)

    async def setSupplyHeatingAdjustMode(self, mode: int) -> None:
        await self._set_int(_REG_SUPPLY_HEATING, mode)

    async def setMaxRH(self, value: int) -> None:
        await self._set_int(_REG_MAX_RH, value)

    async def setMaxCO2(self, value: int) -> None:
        await self._set_int(_REG_MAX_CO2, value)

    async def setBypassSetting(self, enabled: bool) -> None:
        await self._set_flag(_REG_BYPASS_SETTING, enabled)

    async def setSteplessBypass(self, enabled: bool) -> None:
        await self._set_flag(_REG_STEPLESS_BYPASS, enabled)

    async def setCoolHeatRecoveryEnabled(self, enabled: bool) -> None:
        await self._set_flag(_REG_COOL_HEAT_REC_EN, enabled)

    async def setCoolHeatRecovery(self, enabled: bool) -> None:
        await self._set_flag(_REG_COOL_HEAT_REC, enabled)

    async def setHeatExchanger(self, value: int) -> None:
        await self._set_int(_REG_HEAT_EXCHANGER, value)

    async def test_connection(self) -> bool:
        try:
            response = await self._exchangeData(_READ_REQUEST)
            self._parseData(response)
            return True
        except Exception:
            return False

    # ---------------------------------------------------------------------------
    # Sensor array accessors
    # ---------------------------------------------------------------------------

    def rhSensor(self, index: int) -> int | None:
        return self._rhSensors[index]

    def co2Sensor(self, index: int) -> int | None:
        return self._co2Sensors[index]

    def vocSensor(self, index: int) -> int | None:
        return self._vocSensors[index]

    # ---------------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------------

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

    @property
    def BoostTimerRemaining(self) -> int | None:
        return self._boostTimerRemaining

    @property
    def FireplaceTimerRemaining(self) -> int | None:
        return self._fireplaceTimerRemaining

    @property
    def RhControlHome(self) -> bool | None:
        return self._rhControlHome

    @property
    def Co2ControlHome(self) -> bool | None:
        return self._co2ControlHome

    @property
    def RhControlAway(self) -> bool | None:
        return self._rhControlAway

    @property
    def Co2ControlAway(self) -> bool | None:
        return self._co2ControlAway

    @property
    def RhControlBoost(self) -> bool | None:
        return self._rhControlBoost

    @property
    def Co2ControlBoost(self) -> bool | None:
        return self._co2ControlBoost

    @property
    def FilterReminderEnabled(self) -> bool | None:
        return self._filterReminderEnabled

    @property
    def supplyHeatingAdjustMode(self) -> int | None:
        return self._supplyHeatingAdjustMode

    @property
    def maxRH(self) -> int | None:
        return self._maxRH

    @property
    def maxCO2(self) -> int | None:
        return self._maxCO2

    @property
    def BypassSetting(self) -> bool | None:
        return self._bypassSetting

    @property
    def SteplessBypass(self) -> bool | None:
        return self._steplessBypass

    @property
    def CoolHeatRecoveryEnabled(self) -> bool | None:
        return self._coolHeatRecoveryEnabled

    @property
    def CoolHeatRecovery(self) -> bool | None:
        return self._coolHeatRecovery

    @property
    def heatExchanger(self) -> int | None:
        return self._heatExchanger

    @property
    def rhSensorCount(self) -> int:
        return sum(1 for v in self._rhSensors if v is not None)

    @property
    def co2SensorCount(self) -> int:
        return sum(1 for v in self._co2Sensors if v is not None)

    @property
    def vocSensorCount(self) -> int:
        return sum(1 for v in self._vocSensors if v is not None)
