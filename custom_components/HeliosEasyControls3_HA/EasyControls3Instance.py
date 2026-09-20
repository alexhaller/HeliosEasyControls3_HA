# ruff: noqa: N999 -- module/package names are fixed by the HA domain and the upstream project
import asyncio
import datetime
import logging
from typing import cast

from dateutil.relativedelta import relativedelta
from homeassistant.exceptions import HomeAssistantError
from websockets.asyncio.client import connect

from .deviceList import deviceInfo
from .KWLStates import CellState, KWLState

LOGGER = logging.getLogger(__name__)


class WriteRejected(HomeAssistantError):
    """The device did not acknowledge a write command."""


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
_BUF_RH_LEVEL = 70
_BUF_CO2_LEVEL = 71
_BUF_RH_VALUE = 74
_BUF_CO2_VALUE = 75
_BUF_MULTISENSOR_CO2 = 79
_BUF_MULTISENSOR_TEMP = 80
_BUF_MULTISENSOR_RH = 81
_BUF_RH_SENSOR_0 = 84  # ..89
_BUF_CO2_SENSOR_0 = 90  # ..95
_BUF_VOC_SENSOR_0 = 102  # ..105

# Software state (buf_start=106, reg_start=4608)
_BUF_STATE = 107
_BUF_MODE = 108
_BUF_DEFROSTING = 109
_BUF_BOOST_TIMER = 110
_BUF_INDIVIDUAL_TIMER = 111
_BUF_EXTRA_TIMER = 112
_BUF_WEEKLY_TIMER = 113
_BUF_CELL_STATE = 114
_BUF_UPTIME_YEARS = 115
_BUF_UPTIME_HOURS = 116
_BUF_CURRENT_UPTIME = 117
_BUF_FILTER_REMAINING = 118
_BUF_LIMP_MODE = 119
_BUF_EMERGENCY_STOP = 122
_BUF_DEVICE_ENABLED = 124
_BUF_MLV_STATE = 126
_BUF_CLOUD_STATUS = 129

# Output (buf_start=138, reg_start=4864)
_BUF_IO_EXTRACT_FAN = 139
_BUF_IO_SUPPLY_FAN = 140
_BUF_IO_ERROR = 141
_BUF_IO_HEATER = 142
_BUF_IO_EXTRA_HEATER = 143
_BUF_IO_BYPASS = 144

# Settings (buf_start=182, reg_start=20480)
_BUF_EXTR_FAN_BALANCE = 187
_BUF_SUPP_FAN_BALANCE = 188
_BUF_INDIVIDUAL_EXTR_FAN = 189
_BUF_INDIVIDUAL_SUPP_FAN = 190
_BUF_MAX_RH = 192
_BUF_MAX_CO2 = 193
_BUF_EXTRA_ENABLED = 194
_BUF_EXTRA_AIR_TEMP = 195
_BUF_EXTRA_EXTR_FAN = 196
_BUF_EXTRA_SUPP_FAN = 197
_BUF_EXTRA_TIME = 198
_BUF_INDIVIDUAL_AIR_TEMP = 199
_BUF_RH_CTRL_AWAY = 201
_BUF_CO2_CTRL_AWAY = 202
_BUF_AWAY_SPEED = 203
_BUF_AWAY_AIR_TEMP = 204
_BUF_FILTER_REMINDER_DIS = 205  # inverted: 1 = reminder disabled
_BUF_FILTER_REMINDER_AUTO_TIME = 206
_BUF_RH_CTRL_HOME = 207
_BUF_CO2_CTRL_HOME = 208
_BUF_HOME_SPEED = 209
_BUF_HOME_AIR_TEMP = 210
_BUF_MAX_FANSPEED_EXTRACT = 212
_BUF_BOOST_RH_CTRL = 213
_BUF_BOOST_CO2_CTRL = 214
_BUF_BOOST_SPEED = 215
_BUF_BOOST_AIR_TEMP = 216
_BUF_MAX_FANSPEED_SUPPLY = 217
_BUF_COOLRECOVERY_DISABLED = 218  # inverted: 1 = cool recovery off
_BUF_MLV_SUPPLY_LOWER_LIMIT = 223
_BUF_SUPPLY_AIR_DEFROST_TEMP = 224
_BUF_MLV_SUMMER_SETPOINT = 231
_BUF_MLV_WINTER_SETPOINT = 233
_BUF_CELL_TYPE = 240
_BUF_FILTER_INTERVAL = 239  # in days, not months
_BUF_RH_LEVEL_MODE = 245
_BUF_BOOST_DURATION = 246
_BUF_INDIVIDUAL_DURATION = 247
_BUF_FILTER_CHANGED_DAY = 248
_BUF_FILTER_CHANGED_MONTH = 249
_BUF_FILTER_CHANGED_YEAR = 250
_BUF_SUPPLY_HEATING_MODE = 251
_BUF_PARTIAL_BYPASS = 253
_BUF_BYPASS_LOCKED = 254  # inverted: 1 = bypass off
_BUF_POST_HEATER_WINTER_SETPOINT = 256

# Constant flow (buf_start=281, reg_start=32768)
_BUF_CF_AWAY_SUPPLY_AIRFLOW = 282
_BUF_CF_AWAY_EXTRACT_AIRFLOW = 283
_BUF_CF_HOME_SUPPLY_AIRFLOW = 284
_BUF_CF_HOME_EXTRACT_AIRFLOW = 285
_BUF_CF_BOOST_SUPPLY_AIRFLOW = 286
_BUF_CF_BOOST_EXTRACT_AIRFLOW = 287
_BUF_MEASURED_SUPPLY = 290
_BUF_MEASURED_EXTRACT = 291
_BUF_CF_LIMITER_ACTIVE = 293
_BUF_CF_SUPPLY_FANLOAD = 294
_BUF_CF_EXTRACT_FANLOAD = 295

# Extended block (reg_start=46000). The ranges for absent hardware — notably the
# two tornado blocks of a post-heater module — are omitted from the reply, so
# this block's position shifts per unit and has to be resolved at parse time.
_BUF_WEEKLY_SCHEDULE = 497
_EXTENDED_RANGE_WORDS = 39
_EXT_CONDENSATION_PREVENTION = 1
_EXT_SUPPLY_AIRFLOW = 3
_EXT_EXTRACT_AIRFLOW = 4
_EXT_TOR_CONNECTED = 9
_EXT_CF_FAN_SPEED = 14
_EXT_TIMED_ENABLED = 21
_EXT_TIMED_START_DAY = 22
_EXT_TIMED_START_MONTH = 23
_EXT_TIMED_START_YEAR = 24
_EXT_TIMED_END_DAY = 25
_EXT_TIMED_END_MONTH = 26
_EXT_TIMED_END_YEAR = 27
_EXT_TIMED_MODE = 28
_EXT_TIMED_RETURN_MODE = 29
_EXT_CONSTANT_FAN_MAX = 31
_EXT_CONSTANT_FAN_MIN = 32
_EXT_CONSTANT_FAN_BALANCE = 33
_EXT_CONSTANT_AIRFLOW_ALERT = 34

# ---------------------------------------------------------------------------
# Write register addresses
# ---------------------------------------------------------------------------
_REG_STATE = 0x1201
_REG_MODE = 0x1202
_REG_BOOST_TIMER = 0x1204
_REG_INDIVIDUAL_TIMER = 0x1205
_REG_WEEKLY_TIMER = 0x1207
_REG_INDIVIDUAL_EXTR_FAN = 0x5007
_REG_INDIVIDUAL_SUPP_FAN = 0x5008
_REG_MAX_RH = 0x500A
_REG_MAX_CO2 = 0x500B
_REG_EXTRA_AIR_TEMP = 0x500D
_REG_EXTRA_EXTR_FAN = 0x500E
_REG_EXTRA_SUPP_FAN = 0x500F
_REG_EXTRA_TIME = 0x5010
_REG_INDIVIDUAL_AIR_TEMP = 0x5011
_REG_RH_CTRL_AWAY = 0x5013
_REG_CO2_CTRL_AWAY = 0x5014
_REG_AWAY_FAN_SPEED = 0x5015
_REG_AWAY_AIR_TEMP = 0x5016
_REG_FILTER_REMINDER = 0x5017
_REG_RH_CTRL_HOME = 0x5019
_REG_CO2_CTRL_HOME = 0x501A
_REG_HOME_FAN_SPEED = 0x501B
_REG_HOME_AIR_TEMP = 0x501C
_REG_BOOST_RH_CTRL = 0x501F
_REG_BOOST_CO2_CTRL = 0x5020
_REG_BOOST_FAN_SPEED = 0x5021
_REG_BOOST_AIR_TEMP = 0x5022
_REG_COOLRECOVERY_DISABLED = 0x5024
_REG_CELL_TYPE = 0x503A
_REG_BOOST_DURATION = 0x5040
_REG_INDIVIDUAL_DURATION = 0x5041
_REG_SUPPLY_HEATING = 0x5045
_REG_PARTIAL_BYPASS = 0x5047
_REG_BYPASS_LOCKED = 0x5048
_REG_EXTR_FAN_BALANCE = 0x5005
_REG_SUPP_FAN_BALANCE = 0x5006
_REG_EXTRA_ENABLED = 0x500C
_REG_FILTER_REMINDER_AUTO_TIME = 0x5018
_REG_MAX_FANSPEED_EXTRACT = 0x501E
_REG_MAX_FANSPEED_SUPPLY = 0x5023
_REG_MLV_SUPPLY_LOWER_LIMIT = 0x5029
_REG_SUPPLY_AIR_DEFROST_TEMP = 0x502A
_REG_MLV_SUMMER_SETPOINT = 0x5031
_REG_MLV_WINTER_SETPOINT = 0x5033
_REG_RH_LEVEL_MODE = 0x503F
_REG_POST_HEATER_WINTER_SETPOINT = 0x504A
_REG_CF_AWAY_SUPPLY_AIRFLOW = 0x8001
_REG_CF_AWAY_EXTRACT_AIRFLOW = 0x8002
_REG_CF_HOME_SUPPLY_AIRFLOW = 0x8003
_REG_CF_HOME_EXTRACT_AIRFLOW = 0x8004
_REG_CF_BOOST_SUPPLY_AIRFLOW = 0x8005
_REG_CF_BOOST_EXTRACT_AIRFLOW = 0x8006
_REG_TIMED_ENABLED = 46021
_REG_TIMED_START_DAY = 46022
_REG_TIMED_START_MONTH = 46023
_REG_TIMED_START_YEAR = 46024
_REG_TIMED_END_DAY = 46025
_REG_TIMED_END_MONTH = 46026
_REG_TIMED_END_YEAR = 46027
_REG_TIMED_MODE = 46028

_FAN_SPEED_REG: dict[KWLState, int] = {
    KWLState.AtHome: _REG_HOME_FAN_SPEED,
    KWLState.Away: _REG_AWAY_FAN_SPEED,
    KWLState.Intensive: _REG_BOOST_FAN_SPEED,
}

_CF_AIRFLOW_REG: dict[str, int] = {
    "away_supply": _REG_CF_AWAY_SUPPLY_AIRFLOW,
    "away_extract": _REG_CF_AWAY_EXTRACT_AIRFLOW,
    "home_supply": _REG_CF_HOME_SUPPLY_AIRFLOW,
    "home_extract": _REG_CF_HOME_EXTRACT_AIRFLOW,
    "boost_supply": _REG_CF_BOOST_SUPPLY_AIRFLOW,
    "boost_extract": _REG_CF_BOOST_EXTRACT_AIRFLOW,
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


def _date_or_none(day: int, month: int, year: int) -> datetime.date | None:
    """Build a date from the device's day/month/year-since-2000 triplet."""
    try:
        return datetime.date(2000 + year, month, day)
    except ValueError:
        return None


def _find_extended_start(data: bytes) -> int | None:
    """Locate the extended block by walking the reply's range length markers.

    Every range starts with a word holding its own length, so the blocks after
    the weekly schedule can be walked even though the optional post-heater
    ranges may or may not be present.
    """
    total = len(data) // 2
    offset = _BUF_WEEKLY_SCHEDULE
    while offset < total:
        length = _word(data, offset)
        if length == _EXTENDED_RANGE_WORDS:
            return offset
        if length <= 0 or offset + length > total:
            return None
        offset += length
    return None


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
        self._individualAirTempTarget: float | None = None
        self._rhSensors: list[int | None] = [None] * 6
        self._co2Sensors: list[int | None] = [None] * 6
        self._vocSensors: list[int | None] = [None] * 4
        self._boostTimerRemaining: int | None = None
        self._individualTimerRemaining: int | None = None
        self._rhControlHome: bool | None = None
        self._co2ControlHome: bool | None = None
        self._rhControlAway: bool | None = None
        self._co2ControlAway: bool | None = None
        self._rhControlBoost: bool | None = None
        self._co2ControlBoost: bool | None = None
        self._filterReminderEnabled: bool | None = None
        self._extraTimerRemaining: int | None = None
        self._individualExtractFanSpeed: int | None = None
        self._individualSupplyFanSpeed: int | None = None
        self._extraExtractFanSpeed: int | None = None
        self._extraSupplyFanSpeed: int | None = None
        self._extraModeDuration: datetime.time | None = None
        self._individualModeDuration: datetime.time | None = None
        self._supplyHeatingAdjustMode: int | None = None
        self._maxRH: int | None = None
        self._maxCO2: int | None = None
        self._bypassSetting: bool | None = None
        self._steplessBypass: bool | None = None
        self._coolHeatRecovery: bool | None = None
        self._heatExchanger: int | None = None

        # Hardware state
        self._rhLevel: int | None = None
        self._co2Level: int | None = None
        self._co2Value: int | None = None
        self._multisensorTemp: float | None = None
        self._multisensorRH: int | None = None

        # Software state
        self._limpMode: bool | None = None
        self._deviceEnabled: bool | None = None
        self._mlvState: int | None = None
        self._cloudStatus: int | None = None

        # Digital outputs
        self._ioExtractFan: int | None = None
        self._ioSupplyFan: int | None = None
        self._ioError: bool | None = None
        self._ioHeater: bool | None = None
        self._ioExtraHeater: bool | None = None

        # Settings
        self._extractFanBalance: int | None = None
        self._supplyFanBalance: int | None = None
        self._extraEnabled: bool | None = None
        self._filterReminderAutoTime: int | None = None
        self._maxFanSpeedExtract: int | None = None
        self._maxFanSpeedSupply: int | None = None
        self._mlvSupplyLowerLimit: float | None = None
        self._supplyAirDefrostTemp: float | None = None
        self._mlvSummerSetpoint: float | None = None
        self._mlvWinterSetpoint: float | None = None
        self._rhLevelMode: int | None = None
        self._postHeaterWinterSetpoint: float | None = None

        # Constant flow
        self._cfBaseAirflow: dict[str, int | None] = {}
        self._measuredSupply: int | None = None
        self._measuredExtract: int | None = None
        self._cfLimiterActive: bool | None = None
        self._cfSupplyFanLoad: int | None = None
        self._cfExtractFanLoad: int | None = None

        # Extended block
        self._condensationPrevention: int | None = None
        self._supplyAirflow: int | None = None
        self._extractAirflow: int | None = None
        self._torConnected: bool | None = None
        self._cfFanSpeed: int | None = None
        self._timedFunctionEnabled: bool | None = None
        self._timedFunctionStart: datetime.date | None = None
        self._timedFunctionEnd: datetime.date | None = None
        self._timedFunctionMode: int | None = None
        self._timedFunctionReturnMode: int | None = None
        self._constantFanMax: int | None = None
        self._constantFanMin: int | None = None
        self._constantFanBalance: int | None = None
        self._constantAirflowAlert: bool | None = None

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
        if response != _WRITE_OK:
            raise WriteRejected(
                f"{context}: device did not acknowledge the write "
                f"(response {response.hex()})"
            )
        LOGGER.debug("%s: write acknowledged", context)

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
        self._parse_constant_flow(data)
        self._parse_extended(data)

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
        self._rhLevel = _low(data, _BUF_RH_LEVEL)
        self._co2Level = _word(data, _BUF_CO2_LEVEL)
        co2 = _word(data, _BUF_CO2_VALUE)
        self._co2Value = None if co2 in (0, 0xFFFF) else co2
        multi_temp = _word(data, _BUF_MULTISENSOR_TEMP)
        self._multisensorTemp = None if multi_temp == 0xFFFF else float(multi_temp)
        multi_rh = _word(data, _BUF_MULTISENSOR_RH)
        self._multisensorRH = None if multi_rh == 0xFFFF else multi_rh
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
        fire = _word(data, _BUF_INDIVIDUAL_TIMER)
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
        self._individualTimerRemaining = fire
        self._extraTimerRemaining = _word(data, _BUF_EXTRA_TIMER)
        self._weeklyTimerEnabled = bool(_low(data, _BUF_WEEKLY_TIMER))
        cell_raw = _low(data, _BUF_CELL_STATE)
        self._cellState = CellState(cell_raw) if cell_raw < 4 else None
        self._totalUptimeYears = _word(data, _BUF_UPTIME_YEARS)
        self._totalUptimeHours = _word(data, _BUF_UPTIME_HOURS)
        self._currentUptimeHours = _word(data, _BUF_CURRENT_UPTIME)
        self._filterRemainingDays = _word(data, _BUF_FILTER_REMAINING)
        self._emergencyStopActivated = bool(_low(data, _BUF_EMERGENCY_STOP))
        self._limpMode = bool(_low(data, _BUF_LIMP_MODE))
        self._deviceEnabled = bool(_low(data, _BUF_DEVICE_ENABLED))
        self._mlvState = _word(data, _BUF_MLV_STATE)
        self._cloudStatus = _word(data, _BUF_CLOUD_STATUS)

    def _parse_output(self, data: bytes) -> None:
        self._bypassOpen = bool(_low(data, _BUF_IO_BYPASS))
        # The two fan outputs carry the drive level, not an on/off state.
        self._ioExtractFan = _word(data, _BUF_IO_EXTRACT_FAN)
        self._ioSupplyFan = _word(data, _BUF_IO_SUPPLY_FAN)
        self._ioError = bool(_low(data, _BUF_IO_ERROR))
        self._ioHeater = bool(_low(data, _BUF_IO_HEATER))
        self._ioExtraHeater = bool(_low(data, _BUF_IO_EXTRA_HEATER))

    def _parse_settings(self, data: bytes) -> None:
        self._supplyHeatingAdjustMode = _low(data, _BUF_SUPPLY_HEATING_MODE)
        self._individualExtractFanSpeed = _low(data, _BUF_INDIVIDUAL_EXTR_FAN)
        self._individualSupplyFanSpeed = _low(data, _BUF_INDIVIDUAL_SUPP_FAN)
        self._extraAirTempTarget = _kelvin_word_to_celsius(data, _BUF_EXTRA_AIR_TEMP)
        self._extraExtractFanSpeed = _low(data, _BUF_EXTRA_EXTR_FAN)
        self._extraSupplyFanSpeed = _low(data, _BUF_EXTRA_SUPP_FAN)
        self._extraModeDuration = _minutes_to_time(_word(data, _BUF_EXTRA_TIME))
        self._individualAirTempTarget = _kelvin_word_to_celsius(
            data, _BUF_INDIVIDUAL_AIR_TEMP
        )
        self._rhControlAway = bool(_low(data, _BUF_RH_CTRL_AWAY))
        self._co2ControlAway = bool(_low(data, _BUF_CO2_CTRL_AWAY))
        self._awayAirTempTarget = _kelvin_word_to_celsius(data, _BUF_AWAY_AIR_TEMP)
        self._filterReminderEnabled = not bool(_low(data, _BUF_FILTER_REMINDER_DIS))
        self._rhControlHome = bool(_low(data, _BUF_RH_CTRL_HOME))
        self._co2ControlHome = bool(_low(data, _BUF_CO2_CTRL_HOME))
        self._homeAirTempTarget = _kelvin_word_to_celsius(data, _BUF_HOME_AIR_TEMP)
        self._rhControlBoost = bool(_low(data, _BUF_BOOST_RH_CTRL))
        self._co2ControlBoost = bool(_low(data, _BUF_BOOST_CO2_CTRL))
        self._boostAirTempTarget = _kelvin_word_to_celsius(data, _BUF_BOOST_AIR_TEMP)
        self._coolHeatRecovery = not bool(_low(data, _BUF_COOLRECOVERY_DISABLED))
        self._heatExchanger = _low(data, _BUF_CELL_TYPE)
        self._maxCO2 = _word(data, _BUF_MAX_CO2)
        self._maxRH = _low(data, _BUF_MAX_RH)
        self._steplessBypass = bool(_low(data, _BUF_PARTIAL_BYPASS))
        self._bypassSetting = not bool(_low(data, _BUF_BYPASS_LOCKED))
        self._intensivDuration = _minutes_to_time(_word(data, _BUF_BOOST_DURATION))
        self._individualModeDuration = _minutes_to_time(
            _word(data, _BUF_INDIVIDUAL_DURATION)
        )
        self._filterInterval = _word(data, _BUF_FILTER_INTERVAL)
        day = _low(data, _BUF_FILTER_CHANGED_DAY)
        month = _low(data, _BUF_FILTER_CHANGED_MONTH)
        year = 2000 + _low(data, _BUF_FILTER_CHANGED_YEAR)
        self._filterChanged = datetime.date(year, month, day)
        self._filterDue = self._filterChanged + relativedelta(
            days=int(self._filterInterval)
        )
        self._atHomeFanSpeed = _low(data, _BUF_HOME_SPEED)
        self._awayFanSpeed = _low(data, _BUF_AWAY_SPEED)
        self._intensivFanSpeed = _low(data, _BUF_BOOST_SPEED)
        self._extractFanBalance = _low(data, _BUF_EXTR_FAN_BALANCE)
        self._supplyFanBalance = _low(data, _BUF_SUPP_FAN_BALANCE)
        self._extraEnabled = bool(_low(data, _BUF_EXTRA_ENABLED))
        self._filterReminderAutoTime = _word(data, _BUF_FILTER_REMINDER_AUTO_TIME)
        self._maxFanSpeedExtract = _low(data, _BUF_MAX_FANSPEED_EXTRACT)
        self._maxFanSpeedSupply = _low(data, _BUF_MAX_FANSPEED_SUPPLY)
        self._mlvSupplyLowerLimit = _kelvin_word_to_celsius(
            data, _BUF_MLV_SUPPLY_LOWER_LIMIT
        )
        self._supplyAirDefrostTemp = _kelvin_word_to_celsius(
            data, _BUF_SUPPLY_AIR_DEFROST_TEMP
        )
        self._mlvSummerSetpoint = _kelvin_word_to_celsius(
            data, _BUF_MLV_SUMMER_SETPOINT
        )
        self._mlvWinterSetpoint = _kelvin_word_to_celsius(
            data, _BUF_MLV_WINTER_SETPOINT
        )
        self._rhLevelMode = _low(data, _BUF_RH_LEVEL_MODE)
        self._postHeaterWinterSetpoint = _kelvin_word_to_celsius(
            data, _BUF_POST_HEATER_WINTER_SETPOINT
        )

    def _parse_constant_flow(self, data: bytes) -> None:
        self._cfBaseAirflow = {
            "away_supply": _word(data, _BUF_CF_AWAY_SUPPLY_AIRFLOW),
            "away_extract": _word(data, _BUF_CF_AWAY_EXTRACT_AIRFLOW),
            "home_supply": _word(data, _BUF_CF_HOME_SUPPLY_AIRFLOW),
            "home_extract": _word(data, _BUF_CF_HOME_EXTRACT_AIRFLOW),
            "boost_supply": _word(data, _BUF_CF_BOOST_SUPPLY_AIRFLOW),
            "boost_extract": _word(data, _BUF_CF_BOOST_EXTRACT_AIRFLOW),
        }
        self._measuredSupply = _word(data, _BUF_MEASURED_SUPPLY)
        self._measuredExtract = _word(data, _BUF_MEASURED_EXTRACT)
        self._cfLimiterActive = bool(_low(data, _BUF_CF_LIMITER_ACTIVE))
        self._cfSupplyFanLoad = _word(data, _BUF_CF_SUPPLY_FANLOAD)
        self._cfExtractFanLoad = _word(data, _BUF_CF_EXTRACT_FANLOAD)

    def _parse_extended(self, data: bytes) -> None:
        base = _find_extended_start(data)
        if base is None:
            LOGGER.debug("extended range not present in reply")
            return
        self._condensationPrevention = _word(data, base + _EXT_CONDENSATION_PREVENTION)
        self._supplyAirflow = _word(data, base + _EXT_SUPPLY_AIRFLOW)
        self._extractAirflow = _word(data, base + _EXT_EXTRACT_AIRFLOW)
        self._torConnected = bool(_low(data, base + _EXT_TOR_CONNECTED))
        self._cfFanSpeed = _word(data, base + _EXT_CF_FAN_SPEED)
        self._timedFunctionEnabled = bool(_low(data, base + _EXT_TIMED_ENABLED))
        self._timedFunctionStart = _date_or_none(
            _low(data, base + _EXT_TIMED_START_DAY),
            _low(data, base + _EXT_TIMED_START_MONTH),
            _low(data, base + _EXT_TIMED_START_YEAR),
        )
        self._timedFunctionEnd = _date_or_none(
            _low(data, base + _EXT_TIMED_END_DAY),
            _low(data, base + _EXT_TIMED_END_MONTH),
            _low(data, base + _EXT_TIMED_END_YEAR),
        )
        self._timedFunctionMode = _low(data, base + _EXT_TIMED_MODE)
        self._timedFunctionReturnMode = _low(data, base + _EXT_TIMED_RETURN_MODE)
        self._constantFanMax = _word(data, base + _EXT_CONSTANT_FAN_MAX)
        self._constantFanMin = _word(data, base + _EXT_CONSTANT_FAN_MIN)
        self._constantFanBalance = _word(data, base + _EXT_CONSTANT_FAN_BALANCE)
        self._constantAirflowAlert = bool(
            _low(data, base + _EXT_CONSTANT_AIRFLOW_ALERT)
        )

    # ---------------------------------------------------------------------------
    # Write — mode and power
    # ---------------------------------------------------------------------------

    async def switchMode(self, wantedKWLState: KWLState) -> None:
        if wantedKWLState is KWLState.AtHome:
            cmd = self._build_write_command(
                (_REG_STATE, 0), (_REG_BOOST_TIMER, 0), (_REG_INDIVIDUAL_TIMER, 0)
            )
        elif wantedKWLState is KWLState.Away:
            cmd = self._build_write_command(
                (_REG_STATE, 1), (_REG_BOOST_TIMER, 0), (_REG_INDIVIDUAL_TIMER, 0)
            )
        elif wantedKWLState is KWLState.Intensive:
            assert self._intensivDuration is not None
            duration = self._intensivDuration.hour * 60 + self._intensivDuration.minute
            cmd = self._build_write_command(
                (_REG_BOOST_TIMER, duration), (_REG_INDIVIDUAL_TIMER, 0)
            )
        elif wantedKWLState is KWLState.Individual:
            cmd = self._build_write_command(
                (_REG_BOOST_TIMER, 0), (_REG_INDIVIDUAL_TIMER, 0x96)
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
        return max(1, min(100, requestedFanSpeed))

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

    async def setIndividualAirTempTarget(self, celsius: float) -> None:
        await self._set_temperature(_REG_INDIVIDUAL_AIR_TEMP, celsius)

    async def setIndividualExtractFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_INDIVIDUAL_EXTR_FAN, self.checkFanSpeedLimit(speed))

    async def setIndividualSupplyFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_INDIVIDUAL_SUPP_FAN, self.checkFanSpeedLimit(speed))

    async def setExtraExtractFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_EXTRA_EXTR_FAN, self.checkFanSpeedLimit(speed))

    async def setExtraSupplyFanSpeed(self, speed: int) -> None:
        await self._set_int(_REG_EXTRA_SUPP_FAN, self.checkFanSpeedLimit(speed))

    async def setExtraModeDuration(self, t: datetime.time) -> None:
        await self._set_int(_REG_EXTRA_TIME, max(1, min(0x5A0, t.hour * 60 + t.minute)))

    async def setIndividualModeDuration(self, t: datetime.time) -> None:
        await self._set_int(
            _REG_INDIVIDUAL_DURATION, max(1, min(0x5A0, t.hour * 60 + t.minute))
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
        await self._set_flag(_REG_BYPASS_LOCKED, not enabled)

    async def setSteplessBypass(self, enabled: bool) -> None:
        await self._set_flag(_REG_PARTIAL_BYPASS, enabled)

    async def setCoolHeatRecovery(self, enabled: bool) -> None:
        await self._set_flag(_REG_COOLRECOVERY_DISABLED, not enabled)

    async def setHeatExchanger(self, value: int) -> None:
        await self._set_int(_REG_CELL_TYPE, value)

    async def setExtractFanBalance(self, value: int) -> None:
        await self._set_int(_REG_EXTR_FAN_BALANCE, value)

    async def setSupplyFanBalance(self, value: int) -> None:
        await self._set_int(_REG_SUPP_FAN_BALANCE, value)

    async def setExtraEnabled(self, enabled: bool) -> None:
        await self._set_flag(_REG_EXTRA_ENABLED, enabled)

    async def setFilterReminderAutoTime(self, value: int) -> None:
        await self._set_int(_REG_FILTER_REMINDER_AUTO_TIME, value)

    async def setMaxFanSpeedExtract(self, value: int) -> None:
        await self._set_int(_REG_MAX_FANSPEED_EXTRACT, self.checkFanSpeedLimit(value))

    async def setMaxFanSpeedSupply(self, value: int) -> None:
        await self._set_int(_REG_MAX_FANSPEED_SUPPLY, self.checkFanSpeedLimit(value))

    async def setMlvSupplyLowerLimit(self, celsius: float) -> None:
        await self._set_temperature(_REG_MLV_SUPPLY_LOWER_LIMIT, celsius)

    async def setSupplyAirDefrostTemp(self, celsius: float) -> None:
        await self._set_temperature(_REG_SUPPLY_AIR_DEFROST_TEMP, celsius)

    async def setMlvSummerSetpoint(self, celsius: float) -> None:
        await self._set_temperature(_REG_MLV_SUMMER_SETPOINT, celsius)

    async def setMlvWinterSetpoint(self, celsius: float) -> None:
        await self._set_temperature(_REG_MLV_WINTER_SETPOINT, celsius)

    async def setRhLevelMode(self, mode: int) -> None:
        await self._set_int(_REG_RH_LEVEL_MODE, mode)

    async def setPostHeaterWinterSetpoint(self, celsius: float) -> None:
        await self._set_temperature(_REG_POST_HEATER_WINTER_SETPOINT, celsius)

    async def setCfBaseAirflow(self, key: str, value: int) -> None:
        await self._set_int(_CF_AIRFLOW_REG[key], value)

    async def setTimedFunctionEnabled(self, enabled: bool) -> None:
        await self._set_flag(_REG_TIMED_ENABLED, enabled)

    async def setTimedFunctionMode(self, mode: int) -> None:
        await self._set_int(_REG_TIMED_MODE, mode)

    async def setTimedFunctionStart(self, value: datetime.date) -> None:
        await self._set_date(
            (_REG_TIMED_START_DAY, _REG_TIMED_START_MONTH, _REG_TIMED_START_YEAR),
            value,
        )

    async def setTimedFunctionEnd(self, value: datetime.date) -> None:
        await self._set_date(
            (_REG_TIMED_END_DAY, _REG_TIMED_END_MONTH, _REG_TIMED_END_YEAR), value
        )

    async def _set_date(
        self, registers: tuple[int, int, int], value: datetime.date
    ) -> None:
        """Write day, month and year in a single frame so the date stays consistent."""
        day_reg, month_reg, year_reg = registers
        response = await self._exchangeData(
            self._build_write_command(
                (day_reg, value.day),
                (month_reg, value.month),
                (year_reg, value.year - 2000),
            )
        )
        self._check_write_response(response, "date set")

    async def test_connection(self) -> bool:
        try:
            response = await self._exchangeData(_READ_REQUEST)
            self._parseData(response)
            return True
        except Exception:
            LOGGER.debug("test_connection failed", exc_info=True)
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
    def IndividualAirTempTarget(self) -> float | None:
        return self._individualAirTempTarget

    @property
    def ExtraTimerRemaining(self) -> int | None:
        return self._extraTimerRemaining

    @property
    def IndividualExtractFanSpeed(self) -> int | None:
        return self._individualExtractFanSpeed

    @property
    def IndividualSupplyFanSpeed(self) -> int | None:
        return self._individualSupplyFanSpeed

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
    def IndividualModeDuration(self) -> datetime.time | None:
        return self._individualModeDuration

    @property
    def BoostTimerRemaining(self) -> int | None:
        return self._boostTimerRemaining

    @property
    def IndividualTimerRemaining(self) -> int | None:
        return self._individualTimerRemaining

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

    @property
    def rhLevel(self) -> int | None:
        return self._rhLevel

    @property
    def co2Level(self) -> int | None:
        return self._co2Level

    @property
    def co2Value(self) -> int | None:
        return self._co2Value

    @property
    def multisensorTemp(self) -> float | None:
        return self._multisensorTemp

    @property
    def multisensorRH(self) -> int | None:
        return self._multisensorRH

    @property
    def LimpMode(self) -> bool | None:
        return self._limpMode

    @property
    def DeviceEnabled(self) -> bool | None:
        return self._deviceEnabled

    @property
    def MlvState(self) -> int | None:
        return self._mlvState

    @property
    def CloudStatus(self) -> int | None:
        return self._cloudStatus

    @property
    def IoExtractFan(self) -> int | None:
        return self._ioExtractFan

    @property
    def IoSupplyFan(self) -> int | None:
        return self._ioSupplyFan

    @property
    def IoError(self) -> bool | None:
        return self._ioError

    @property
    def IoHeater(self) -> bool | None:
        return self._ioHeater

    @property
    def IoExtraHeater(self) -> bool | None:
        return self._ioExtraHeater

    @property
    def extractFanBalance(self) -> int | None:
        return self._extractFanBalance

    @property
    def supplyFanBalance(self) -> int | None:
        return self._supplyFanBalance

    @property
    def ExtraEnabled(self) -> bool | None:
        return self._extraEnabled

    @property
    def filterReminderAutoTime(self) -> int | None:
        return self._filterReminderAutoTime

    @property
    def maxFanSpeedExtract(self) -> int | None:
        return self._maxFanSpeedExtract

    @property
    def maxFanSpeedSupply(self) -> int | None:
        return self._maxFanSpeedSupply

    @property
    def mlvSupplyLowerLimit(self) -> float | None:
        return self._mlvSupplyLowerLimit

    @property
    def supplyAirDefrostTemp(self) -> float | None:
        return self._supplyAirDefrostTemp

    @property
    def mlvSummerSetpoint(self) -> float | None:
        return self._mlvSummerSetpoint

    @property
    def mlvWinterSetpoint(self) -> float | None:
        return self._mlvWinterSetpoint

    @property
    def rhLevelMode(self) -> int | None:
        return self._rhLevelMode

    @property
    def postHeaterWinterSetpoint(self) -> float | None:
        return self._postHeaterWinterSetpoint

    def cfBaseAirflow(self, key: str) -> int | None:
        return self._cfBaseAirflow.get(key)

    @property
    def MeasuredSupply(self) -> int | None:
        return self._measuredSupply

    @property
    def MeasuredExtract(self) -> int | None:
        return self._measuredExtract

    @property
    def CfLimiterActive(self) -> bool | None:
        return self._cfLimiterActive

    @property
    def cfSupplyFanLoad(self) -> int | None:
        return self._cfSupplyFanLoad

    @property
    def cfExtractFanLoad(self) -> int | None:
        return self._cfExtractFanLoad

    @property
    def condensationPrevention(self) -> int | None:
        return self._condensationPrevention

    @property
    def SupplyAirflow(self) -> int | None:
        return self._supplyAirflow

    @property
    def ExtractAirflow(self) -> int | None:
        return self._extractAirflow

    @property
    def TorConnected(self) -> bool | None:
        return self._torConnected

    @property
    def cfFanSpeed(self) -> int | None:
        return self._cfFanSpeed

    @property
    def TimedFunctionEnabled(self) -> bool | None:
        return self._timedFunctionEnabled

    @property
    def TimedFunctionStart(self) -> datetime.date | None:
        return self._timedFunctionStart

    @property
    def TimedFunctionEnd(self) -> datetime.date | None:
        return self._timedFunctionEnd

    @property
    def timedFunctionMode(self) -> int | None:
        return self._timedFunctionMode

    @property
    def timedFunctionReturnMode(self) -> int | None:
        return self._timedFunctionReturnMode

    @property
    def constantFanMax(self) -> int | None:
        return self._constantFanMax

    @property
    def constantFanMin(self) -> int | None:
        return self._constantFanMin

    @property
    def constantFanBalance(self) -> int | None:
        return self._constantFanBalance

    @property
    def ConstantAirflowAlert(self) -> bool | None:
        return self._constantAirflowAlert
