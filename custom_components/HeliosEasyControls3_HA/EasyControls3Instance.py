import asyncio
import datetime
import logging
from typing import cast

from dateutil.relativedelta import relativedelta
from websockets.asyncio.client import connect

from .deviceList import deviceInfo
from .KWLStates import KWLState

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
        self._CO2Value: int | None = None
        self._isOn: bool | None = None

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
        # Binary protocol: KWL device responds with structured data at specific byte offsets

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

        # Humidity (offset 74)
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

        # Intensive mode duration in minutes (offset 493)
        intensivDurationInMinutes = data[493]
        intensivDurationHours = intensivDurationInMinutes // 60
        intensivDurationMinutes = intensivDurationInMinutes - 60 * intensivDurationHours
        self._intensivDuration = datetime.time(
            intensivDurationHours, intensivDurationMinutes
        )

        # Device power state (offset 217): 0=on, !=0=off
        self._isOn = bool(data[217] == 0)

        # CO2 sensor value (offsets 182-183)
        self._CO2Value = int(data[182]) << 8 | int(data[183])

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
        requestedSpeedPlainString = self.createFanSpeedPlainRequestString(
            requestedFanSpeed
        )
        requestedSpeedModdedString = self.createFanSpeedModdedRequestString(
            requestedFanSpeed, mode
        )

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
    def CO2Value(self) -> int | None:
        return self._CO2Value
