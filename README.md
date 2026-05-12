# Helios easyControls 3.0 — Home Assistant Integration

HACS custom integration for the **Helios KWL easyControls 3.0** ventilation unit. Communication uses the Vallox WebSocket protocol on port 80.

## Installation

1. Add via HACS as a custom repository
2. After restart, search for **HeliosEasyControls3_HA** in the integration setup
3. Enter the device's IP address — no credentials required

The integration uses the device serial number for stable unique entity IDs (survive IP changes).

---

## Entities

All entities belong to a single HA device. Within the device card:
- **Main area**: operational sensors and controls
- **Konfiguration** (`EntityCategory.CONFIG`): all writable settings
- **Diagnose** (`EntityCategory.DIAGNOSTIC`): device metadata and uptime

### Sensors (operational)
| Entity | Description |
|---|---|
| Outside / Supply / Indoor / Exhaust Temperature | Air temperatures (°C) |
| Supply Cell Air Temperature | Heat exchanger cell temperature (°C) |
| Air Relative Humidity | Internal humidity sensor (%) |
| RH Sensor 0–5 | External RH sensors, only shown if present |
| CO2 Sensor 0–5 | External CO2 sensors (ppm), only shown if present |
| VOC Sensor 0–3 | External VOC sensors (ppm), only shown if present |
| Current Fan Speed | Current ventilation level (%) |
| Extract Fan RPM / Supply Fan RPM | Actual fan speed (RPM) |
| Cell State | Heat recovery / Cool recovery / Bypass / Defrost |
| Heat Recovery Efficiency | Calculated η = (T_supply − T_outside) / (T_indoor − T_outside) |
| Intensive / Extra / Individual Mode Timer Remaining | Minutes left in active mode |
| Defrosting | Binary: defrost cycle active |
| Emergency Stop | Binary: emergency stop activated |
| Bypass Open | Binary: bypass relay state |

### Sensors (diagnostic)
| Entity | Description |
|---|---|
| Last / Next Filter Change | Dates |
| Filter Remaining Days | Days until filter change due |
| Total Uptime Years / Hours | Cumulative device runtime |
| Current Uptime Hours | Runtime since last restart |
| RH / CO2 / VOC Sensor Count | Number of connected external sensors |

### Controls
| Entity | Type | Description |
|---|---|---|
| KWL State | Select | Operating mode: AtHome / Away / Intensive / Individual |
| On/Off | Switch | Power the unit on or off |

### Configuration (Konfiguration)
| Entity | Type | Description |
|---|---|---|
| Fan Speed At Home / Away / Intensive | Number (%) | Target fan speed per profile |
| Individual Extract / Supply Fan Speed | Number (%) | Per-fan speed for Individual mode |
| Extra Extract / Supply Fan Speed | Number (%) | Per-fan speed for Extra mode |
| Home / Away / Intensive / Extra / Individual Air Temp Target | Number (°C) | Supply air temperature target per profile |
| RH Control Home / Away / Intensive | Switch | Enable humidity-driven fan speed |
| CO2 Control Home / Away / Intensive | Switch | Enable CO2-driven fan speed |
| RH Limit | Number (%) | Global humidity threshold |
| CO2/VOC Limit | Number (ppm) | Global CO2/VOC threshold |
| Intensive Mode Duration | Time | Duration for boost mode timer |
| Extra Mode Duration | Time | Duration for extra mode timer |
| Individual Mode Duration | Time | Duration for individual mode timer |
| Weekly Timer | Switch | Enable weekly schedule program |
| Filter Reminder | Switch | Enable filter change reminder |
| Temperature Control Mode | Select | Supply / Extract / Extract+ |
| Heat Exchanger | Select | Rotary / Cell ⚠️ enum values unverified on device |
| Bypass | Switch | Manual bypass enable |
| Stepless Bypass | Switch | Stepless bypass enable |
| Bypass Max Outdoor Temperature | Number (°C) | Upper outdoor temp limit for bypass |
| Cool Recovery Enabled | Switch | Plug removed confirmation |
| Cool Recovery | Switch | Activate cool recovery mode |

---

## Register Map

### Protocol overview

The device uses the Vallox WebSocket binary protocol. A single request (`03 00 F6 00 00 00 F9 00`) returns all data in one frame. Writes use `F9 00` frames with register/value pairs.

**Buffer offset formula**: `buf_offset = group_buf_start + (register − group_reg_start)`  
**Read**: `data[buf_offset × 2]` (high byte), `data[buf_offset × 2 + 1]` (low byte)  
**Temperature encoding**: `kelvin × 100 = round((celsius + 273.15) × 100)`

**Write frame format**:
```
length_LE(2) + 0xF900(2) + N×(register_LE(2) + value_LE(2)) + checksum_LE(2)
length   = N×4 + 2
checksum = sum of all 16-bit LE words & 0xFFFF
```
Expected success response: `02 00 F5 00 F7 00`

**Important**: The **general info, hardware state, software state and output** register ranges (0x0001–0x12F6) are shared with the open-source Vallox WebSocket API. The **settings range (0x5000+) is Helios-specific** — Vallox uses a completely different layout there. Register names in the 0x5000+ section below are Helios-derived, not Vallox API names.

Full Vallox API register reference: https://github.com/yozik04/vallox_websocket_api

---

### Group: General Info — buf = reg (reg 1–26)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 1–10 | 0x01–0x0A | 1–10 | A_CYC_APPL_SW_VERSION_0..9 | ❌ not read | Application SW version (chars/words) |
| 11 | 0x0B | 11 | A_CYC_BOOT_SW_VERSION | ❌ not read | Boot SW version |
| 12–13 | 0x0C–0x0D | 12–13 | A_CYC_APPL_SW_SIZE_0..1 | ❌ not read | Application SW size |
| 14 | 0x0E | 14 | A_CYC_SERIAL_NUMBER_MSW | ✅ read | High word of serial number |
| 15 | 0x0F | 15 | A_CYC_SERIAL_NUMBER_LSW | ✅ read | Low word of serial number |
| 16 | 0x10 | 16 | A_CYC_MACHINE_TYPE | ✅ read | Device type index (deviceList lookup) |
| 17 | 0x11 | 17 | A_CYC_MACHINE_MODEL | ✅ read | Device model index (deviceList lookup) |
| 18 | 0x12 | 18 | A_CYC_MASTER_PASSWORD | ❌ not read | — |
| 19–24 | — | 19–24 | A_CYC_CONFIGURATION_* | ❌ not read | Configuration flags/checksum |
| 26 | 0x1A | 26 | A_CYC_NO_HANDEDNESS | ❌ not read | Device orientation: 0=symmetric, 1=right, 2=left |

---

### Group: Hardware State — buf 63, reg 4352 (0x1100)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 4353 | 0x1101 | 64 | A_CYC_FAN_SPEED | ✅ read | Current fan speed % (= CurrentFanSpeed) |
| 4354 | 0x1102 | 65 | A_CYC_TEMP_EXTRACT_AIR | ✅ read | Indoor/extract temperature (°C) |
| 4355 | 0x1103 | 66 | A_CYC_TEMP_EXHAUST_AIR | ✅ read | Exhaust temperature (°C) |
| 4356 | 0x1104 | 67 | A_CYC_TEMP_OUTDOOR_AIR | ✅ read | Outside temperature (°C) |
| 4357 | 0x1105 | 68 | A_CYC_TEMP_SUPPLY_CELL_AIR | ✅ read | Supply cell air temperature (°C) |
| 4358 | 0x1106 | 69 | A_CYC_TEMP_SUPPLY_AIR | ✅ read | Supply air temperature (°C) |
| 4359 | 0x1107 | 70 | A_CYC_RH_LEVEL | ❌ not read | Computed RH level (%) |
| 4360 | 0x1108 | 71 | A_CYC_CO2_LEVEL | ❌ not read | Computed CO2 level |
| 4361 | 0x1109 | 72 | A_CYC_EXTR_FAN_SPEED | ✅ read | Extract fan RPM |
| 4362 | 0x110A | 73 | A_CYC_SUPP_FAN_SPEED | ✅ read | Supply fan RPM |
| 4363 | 0x110B | 74 | A_CYC_RH_VALUE | ✅ read | Relative humidity % (= AirRH) |
| 4364 | 0x110C | 75 | A_CYC_CO2_VALUE | ❌ not read | CO2 value at main sensor |
| 4365 | 0x110D | 76 | A_CYC_FIREPLACE_SWITCH | ❌ not read | Individual mode switch input |
| 4366 | 0x110E | 77 | A_CYC_DIGITAL_INPUT | ❌ not read | Digital input state |
| 4367 | 0x110F | 78 | A_CYC_ANALOG_CTRL_INPUT | ❌ not read | Analog control input |
| 4368 | 0x1110 | 79 | A_CYC_MULTISENSOR_CO2 | ❌ not read | Multi-sensor CO2 |
| 4369 | 0x1111 | 80 | A_CYC_MULTISENSOR_TEMP | ❌ not read | Multi-sensor temperature |
| 4370 | 0x1112 | 81 | A_CYC_MULTISENSOR_RH | ❌ not read | Multi-sensor RH |
| 4371 | 0x1113 | 82 | A_CYC_VOLTAGE_LOW | ❌ not read | Low voltage flag |
| 4372 | 0x1114 | 83 | A_CYC_ANALOG_SENSOR_INPUT | ❌ not read | Analog sensor input |
| 4373–4378 | 0x1115–0x111A | 84–89 | A_CYC_RH_SENSOR_0..5 | ✅ read | External RH sensors (0xFFFF = absent) |
| 4379–4384 | 0x111B–0x1120 | 90–95 | A_CYC_CO2_SENSOR_0..5 | ✅ read | External CO2 sensors (0xFFFF = absent) |
| 4385–4388 | 0x1121–0x1124 | 96–99 | A_CYC_DIP_SWITCH_0..3 | ❌ not read | DIP switch states |
| 4389 | 0x1125 | 100 | A_CYC_TEMP_OPTIONAL | ❌ not read | Optional temperature sensor |
| 4390 | 0x1126 | 101 | A_CYC_VOC_LEVEL | ❌ not read | Computed VOC level |
| 4391–4394 | 0x1127–0x112A | 102–105 | A_CYC_VOC_SENSOR_0..3 | ✅ read | External VOC sensors (0xFFFF = absent) |

---

### Group: Software State — buf 106, reg 4608 (0x1200)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 4609 | 0x1201 | 107 | A_CYC_STATE | ✅ read/write | Operating mode (0=AtHome, …) |
| 4610 | 0x1202 | 108 | A_CYC_MODE | ✅ read/write | 0=on, ≠0=off |
| 4611 | 0x1203 | 109 | A_CYC_DEFROSTING | ✅ read | bool: defrost active |
| 4612 | 0x1204 | 110 | A_CYC_BOOST_TIMER | ✅ read/write | Intensive timer remaining (min) |
| 4613 | 0x1205 | 111 | A_CYC_FIREPLACE_TIMER | ✅ read/write | Individual timer remaining (min) |
| 4614 | 0x1206 | 112 | A_CYC_EXTRA_TIMER | ✅ read | Extra timer remaining (min) |
| 4615 | 0x1207 | 113 | A_CYC_WEEKLY_TIMER_ENABLED | ✅ read/write | bool |
| 4616 | 0x1208 | 114 | A_CYC_CELL_STATE | ✅ read | 0=HeatRecovery 1=CoolRecovery 2=Bypass 3=Defrost |
| 4617 | 0x1209 | 115 | A_CYC_TOTAL_UP_TIME_YEARS | ✅ read | years |
| 4618 | 0x120A | 116 | A_CYC_TOTAL_UP_TIME_HOURS | ✅ read | hours |
| 4619 | 0x120B | 117 | A_CYC_CURRENT_UP_TIME_HOURS | ✅ read | hours |
| 4620 | 0x120C | 118 | A_CYC_REMAINING_TIME_FOR_FILTER | ✅ read | days |
| 4621 | 0x120D | 119 | A_CYC_LIMP_MODE | ❌ not read | Limp mode active |
| 4622 | 0x120E | 120 | A_CYC_METRICS | ❌ not read | Metrics register |
| 4623 | 0x120F | 121 | A_CYC_MIN_FAN_START_SPEED | ❌ not read | Minimum fan start speed |
| 4624 | 0x1210 | 122 | A_CYC_EMERGENCY_STOP_IS_ACTIVATED | ✅ read | bool |
| 4625 | 0x1211 | 123 | A_CYC_DEFROST_SUPERMELT_THRESHOLD | ❌ not read | Defrost threshold |
| 4626 | 0x1212 | 124 | A_CYC_ENABLED | ❌ not read | Device enabled flag |
| 4627 | 0x1213 | 125 | A_CYC_COMMAND | ❌ not read | Command register |
| 4628 | 0x1214 | 126 | A_CYC_MLV_STATE | ❌ not read | MLV (motor-driven valve) state |
| 4629–4630 | — | 127–128 | A_CYC_UPD_ADDRESS_1..2 | ❌ not read | Update address |
| 4631 | 0x1217 | 129 | A_CYC_CLOUD_STATUS | ❌ not read | Cloud connectivity status |
| 4632 | 0x1218 | 130 | A_CYC_ANALOG_RH_SENSOR_PRSENT | ❌ not read | Analog RH sensor present |

---

### Group: Time — buf ~241, reg 4849 (0x12E1)

| Reg | Hex | Name | Status | Notes |
|---|---|---|---|---|
| 4849–4854 | 0x12E1–0x12E6 | A_CYC_MINUTE / HOUR / DAY / MONTH / YEAR / WEEKDAY | ❌ not read | Device clock — could be used for time sync |

---

### Group: Digital Outputs — buf 138, reg 4864 (0x12F0 area)

> Note: output buf_start=138, reg_start=4864, so buf = 138 + (reg − 4864)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 4865 | 0x12F1 | 139 | A_CYC_IO_EXTRACT_FAN | ❌ not read | Extract fan relay output |
| 4866 | 0x12F2 | 140 | A_CYC_IO_SUPPLY_FAN | ❌ not read | Supply fan relay output |
| 4867 | 0x12F3 | 141 | A_CYC_IO_ERROR | ❌ not read | Error relay output |
| 4868 | 0x12F4 | 142 | A_CYC_IO_HEATER | ❌ not read | Heater relay output |
| 4869 | 0x12F5 | 143 | A_CYC_IO_EXTRA_HEATER | ❌ not read | Extra heater relay output |
| 4870 | 0x12F6 | 144 | A_CYC_IO_BYPASS | ✅ read | Bypass relay state (= BypassOpen) |

---

### Group: Digital Inputs — reg 5121 (0x1401)

| Reg | Hex | Name | Status | Notes |
|---|---|---|---|---|
| 5121–5126 | 0x1401–0x1406 | A_CYC_IN_EXTRACT_FAN / SUPPLY_FAN / ERROR / HEATER / EXTRA_HEATER / BYPASS | ❌ not read | Digital input states |

---

### Group: Configuration — reg 8192 (0x2000)

> Buffer position in the response frame is unknown. May require a separate request.

| Reg | Hex | Name | Status | Notes |
|---|---|---|---|---|
| 8194–8195 | 0x2002–0x2003 | A_CYC_GW_ADDRESS_1..2 | ❌ not read | Gateway IP |
| 8196–8197 | 0x2004–0x2005 | A_CYC_MASK_ADDRESS_1..2 | ❌ not read | Subnet mask |
| 8211 | 0x2013 | A_CYC_ETH_CLOUD_ENABLED | ❌ not read | Cloud / Ethernet enabled |
| 8212–8213 | 0x2014–0x2015 | A_CYC_IP_ADDRESS_1..2 | ❌ not read | Device IP address |
| 8214–8221 | 0x2016–0x201D | A_CYC_UUID0..7 | ❌ not read | Device UUID (8 words) |

---

### Group: Settings — buf 182, reg 20480 (0x5000) — **Helios-specific layout**

> ⚠️ The Vallox open-source API uses a completely different layout in the 0x5000 range. The register names and assignments below are Helios-specific, derived from reverse engineering and verified against a real device.

> ⚠️ **Known label bug**: The Home/Away grouping for RH/CO2 control switches (0x5013/0x5014 and 0x5019/0x501A) appears to be swapped relative to the surrounding fan speed and temperature registers. This needs verification on a device.

| Reg | Hex | Buf | Name (Helios-specific) | Status | Notes |
|---|---|---|---|---|---|
| 20480 | 0x5000 | 182 | — | ❌ not read | unknown |
| 20481 | 0x5001 | 183 | A_CYC_SUPPLY_HEATING_ADJUST_MODE | ✅ read/write | 0=Supply 1=Extract 2=Extract+ |
| 20482–20486 | 0x5002–0x5006 | 184–188 | — | ❌ not read | Modbus / fan balance (Vallox) or unknown (Helios) |
| 20487 | 0x5007 | 189 | A_CYC_FIREPLACE_EXTR_FAN | ✅ read/write | Individual extract fan % |
| 20488 | 0x5008 | 190 | A_CYC_FIREPLACE_SUPP_FAN | ✅ read/write | Individual supply fan % |
| 20489 | 0x5009 | 191 | A_CYC_PARTIAL_BYPASS_DISABLED | ❌ not read | Partial bypass disabled flag |
| 20490 | 0x500A | 192 | A_CYC_RH_BASIC_LEVEL | ❌ not read | RH basic level |
| 20491 | 0x500B | 193 | A_CYC_CO2_THRESHOLD | ❌ not read | CO2 threshold (Vallox name; Helios may differ) |
| 20492 | 0x500C | 194 | A_CYC_EXTRA_ENABLED | ❌ not read | Extra mode enabled |
| 20493 | 0x500D | 195 | A_CYC_EXTRA_AIR_TEMP_TARGET | ✅ read/write | Extra air temp target (°C) |
| 20494 | 0x500E | 196 | A_CYC_EXTRA_EXTR_FAN | ✅ read/write | Extra extract fan % |
| 20495 | 0x500F | 197 | A_CYC_EXTRA_SUPP_FAN | ✅ read/write | Extra supply fan % |
| 20496 | 0x5010 | 198 | A_CYC_EXTRA_TIME | ✅ read/write | Extra mode duration (min) |
| 20497 | 0x5011 | 199 | A_CYC_FIREPLACE_AIR_TEMP_TARGET | ✅ read/write | Individual air temp target (°C) |
| 20498 | 0x5012 | 200 | — | ❌ not read | unknown |
| 20499 | 0x5013 | 201 | A_CYC_AWAY_RH_CTRL_ENABLED ⚠️ | ✅ read/write | Labeled "Home" in HA — may be Away |
| 20500 | 0x5014 | 202 | A_CYC_AWAY_CO2_CTRL_ENABLED ⚠️ | ✅ read/write | Labeled "Home" in HA — may be Away |
| 20501 | 0x5015 | 203 | A_CYC_AWAY_SPEED_SETTING | ✅ read | Away fan speed % |
| 20502 | 0x5016 | 204 | A_CYC_AWAY_AIR_TEMP_TARGET | ✅ read/write | Away air temp target (°C) |
| 20503 | 0x5017 | 205 | A_CYC_FILTER_REMINDER_DISABLED | ✅ read/write | Inverted: 1=reminder off |
| 20504 | 0x5018 | 206 | A_CYC_FILTER_REMINDER_AUTOMATIC_TIME | ❌ not read | Automatic filter reminder interval |
| 20505 | 0x5019 | 207 | A_CYC_HOME_RH_CTRL_ENABLED ⚠️ | ✅ read/write | Labeled "Away" in HA — may be Home |
| 20506 | 0x501A | 208 | A_CYC_HOME_CO2_CTRL_ENABLED ⚠️ | ✅ read/write | Labeled "Away" in HA — may be Home |
| 20507 | 0x501B | 209 | A_CYC_HOME_SPEED_SETTING | ✅ read | AtHome fan speed % |
| 20508 | 0x501C | 210 | A_CYC_HOME_AIR_TEMP_TARGET | ✅ read/write | Home air temp target (°C) |
| 20509 | 0x501D | 211 | A_CYC_DEFROST_RPM_LIMIT | ❌ not read | Defrost fan speed limit |
| 20510 | 0x501E | 212 | A_CYC_MAX_FANSPEED_SCALING_EXTRACT | ❌ not read | Max extract fan scaling |
| 20511 | 0x501F | 213 | A_CYC_BOOST_RH_CTRL_ENABLED | ✅ read/write | Intensive RH control |
| 20512 | 0x5020 | 214 | A_CYC_BOOST_CO2_CTRL_ENABLED | ✅ read/write | Intensive CO2 control |
| 20513 | 0x5021 | 215 | A_CYC_BOOST_SPEED_SETTING | ✅ read | Intensive fan speed % |
| 20514 | 0x5022 | 216 | A_CYC_BOOST_AIR_TEMP_TARGET | ✅ read/write | Intensive air temp target (°C) |
| 20515 | 0x5023 | 217 | A_CYC_MAX_FANSPEED_SCALING_SUPPLY | ❌ not read | Max supply fan scaling |
| 20516 | 0x5024 | 218 | A_CYC_COOLRECOVERY_DISABLED | ❌ not read | Cool recovery disabled flag |
| 20517 | 0x5025 | 219 | A_CYC_COOL_HEAT_RECOVERY_ENABLED | ✅ read/write | Plug removed confirmation |
| 20518 | 0x5026 | 220 | A_CYC_COOL_HEAT_RECOVERY | ✅ read/write | Cool recovery active |
| 20519 | 0x5027 | 221 | — | ❌ not read | unknown |
| 20520 | 0x5028 | 222 | A_CYC_HEAT_EXCHANGER | ✅ read/write | ⚠️ enum values unverified |
| 20521 | 0x5029 | 223 | A_CYC_MAX_CO2 | ✅ read/write | CO2/VOC limit (ppm, 16-bit) |
| 20522 | 0x502A | 224 | — | ❌ not read | unknown |
| 20523 | 0x502B | 225 | A_CYC_MAX_RH | ✅ read/write | RH limit (%) |
| 20524 | 0x502C | 226 | A_CYC_BYPASS_MAX_OUTDOOR_TEMP | ✅ read/write | Max outdoor temp for bypass (°C) |
| 20525 | 0x502D | 227 | A_CYC_STEPLESS_BYPASS | ✅ read/write | Stepless bypass enable |
| 20526 | 0x502E | 228 | — | ❌ not read | unknown |
| 20527 | 0x502F | 229 | — | ❌ not read | unknown |
| 20528 | 0x5030 | 230 | A_CYC_BYPASS_SETTING | ✅ read/write | Bypass manual enable |
| 20529–20536 | 0x5031–0x5038 | 231–238 | — | ❌ not read | MLV / waterheater / defrost params |
| 20537 | 0x5039 | 239 | A_CYC_FILTER_CHANGE_INTERVAL | ✅ read | Filter interval (months) |
| 20538 | 0x503A | 240 | A_CYC_CELL_TYPE | ❌ not read | Cell/heat exchanger type |
| 20539–20542 | 0x503B–0x503E | 241–244 | A_CYC_EXTRA_HEATER_TYPE / POST_HEATER_TYPE / BRANDING / SIDEDNESS | ❌ not read | Sidedness = orientation on Vallox std |
| 20543 | 0x503F | 245 | A_CYC_RH_LEVEL_MODE | ❌ not read | Humidity mode: Auto/Manual |
| 20544 | 0x5040 | 246 | A_CYC_BOOST_TIME | ✅ read/write | Intensive mode duration (min) |
| 20545 | 0x5041 | 247 | A_CYC_FIREPLACE_TIME | ✅ read/write | Individual mode duration (min) |
| 20546 | 0x5042 | 248 | A_CYC_FILTER_CHANGED_DAY | ✅ read | Last filter change day |
| 20547 | 0x5043 | 249 | A_CYC_FILTER_CHANGED_MONTH | ✅ read | Last filter change month |
| 20548 | 0x5044 | 250 | A_CYC_FILTER_CHANGED_YEAR | ✅ read | Last filter change year (+2000) |
| 20549 | 0x5045 | 251 | A_CYC_SUPPLY_HEATING_ADJUST_MODE (Vallox std) | ❌ not read | In Vallox std this is the heating mode; Helios uses 0x5001 instead |
| 20550–20552 | 0x5046–0x5048 | 252–254 | A_CYC_MIN_DEFROST_TIME / PARTIAL_BYPASS / BYPASS_LOCKED | ❌ not read | In Vallox: partial bypass % + bypass lock |
| 20553–20555 | 0x5049–0x504B | 255–257 | A_CYC_OPT_TEMP_SENSOR_MODE / POST_HEATER_WINTER_SETPOINT / DEWPOINT_LIMIT_IN_USE | ❌ not read | — |

---

### Typhoon Settings — reg 21761 (0x5500)

| Reg | Hex | Name | Status | Notes |
|---|---|---|---|---|
| 21761 | 0x5501 | A_CYC_LANGUAGE | ❌ not read | Display language |
| 21766 | 0x5506 | A_CYC_BOOST_TIMER_ENABLED | ❌ not read | Boost timer enable |
| 21767 | 0x5507 | A_CYC_FIREPLACE_TIMER_ENABLED | ❌ not read | Individual timer enable |
| 21772 | 0x550C | A_CYC_EXTRA_TIMER_ENABLED | ❌ not read | Extra timer enable |

---

### Weekly Schedule — reg 40961–41128 (0xA001–0xA0C8)

168 entries (7 days × 24 hours). Each entry stores a profile value (0=None, 1=Home, 2=Away, 3=Intensive, 4=Individual, 5=Extra).

| Status | Notes |
|---|---|
| ❌ not read/written | Would enable full weekly schedule management from HA |

---

### Faults — reg 36865+ (0x9001+)

| Reg | Hex | Name | Status |
|---|---|---|---|
| 36865 | 0x9001 | A_CYC_TOTAL_FAULT_COUNT | ❌ not read |
| 36866+ | 0x9002+ | A_CYC_FAULT_CODE, SEVERITY, FIRST_DATE, LAST_DATE, COUNT, ACTIVITY (×34) | ❌ not read |

---

## Implementable next (known registers, just not coded yet)

| Register(s) | Name | Where |
|---|---|---|
| buf 1–10 (reg 1–10) | Application SW version | General info |
| buf 26 (reg 26) | Device orientation (A_CYC_NO_HANDEDNESS) | General info |
| buf 245 (0x503F) | Humidity mode Auto/Manual (A_CYC_RH_LEVEL_MODE) | Settings |
| buf 240 (0x503A) | Cell type (A_CYC_CELL_TYPE) | Settings — may be same as Heat Exchanger |
| buf 144–148 (0x12F1–0x12F5) | IO relay states: extract/supply fan, error, heater, extra heater | Output |
| reg 36865+ | Fault history | Faults group |
| reg 40961–41128 | Full weekly schedule (168 hourly slots) | Weekly schedule |

## Pending verification

| Item | Action needed |
|---|---|
| RH/CO2 Control Home/Away labels (0x5013/0x5019) | Verify on device: enable "RH Control Home" and check which profile changes |
| Heat Exchanger enum (0x5028) | Read raw value from device and confirm 0=Rotary, 1=Cell |
| Settings 0x5025–0x5028 semantics | Confirm Helios firmware meaning for cool recovery / relay mode / digital input registers |
