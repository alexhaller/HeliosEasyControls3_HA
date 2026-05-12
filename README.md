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
| Intensive / Extra / Individual Mode Timer Remaining | Minutes left in active boost/extra/individual mode |
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
| Heat Exchanger | Select | Rotary / Cell ⚠️ verify enum on device |
| Bypass | Switch | Manual bypass enable |
| Stepless Bypass | Switch | Stepless bypass enable |
| Bypass Max Outdoor Temperature | Number (°C) | Upper outdoor temp limit for bypass |
| Cool Recovery Enabled | Switch | Plug removed confirmation |
| Cool Recovery | Switch | Activate cool recovery mode |

---

## Register Map

The device uses the Vallox WebSocket binary protocol. One request (`0300f6000000f900`) returns all data in a single frame. Writes use `0xF9 0x00` frames with register/value pairs.

**Buffer offset formula**: `buf_offset = group_buf_start + (register − group_reg_start)`  
**Read**: `data[buf_offset × 2]` (high byte) and `data[buf_offset × 2 + 1]` (low byte)  
**Temperature encoding**: `kelvin × 100 = round((celsius + 273.15) × 100)`

Full Vallox register specification: https://github.com/yozik04/vallox_websocket_api

### Group: g_cyclone_hw_state — buf 63, reg 4352 (0x1100)

| Reg | Hex | Buf | Register name | Status | Notes |
|---|---|---|---|---|---|
| 4352 | 0x1100 | 63 | A_CYC_MACHINE_MODEL | ❌ not read | device model index |
| 4353 | 0x1101 | 64 | A_CYC_SERIAL_NUMBER_… | ✅ read | 32-bit, buf 14–17 (different frame offsets) |
| 4354–4355 | — | 65–66 | A_CYC_TEMP_INDOOR / EXHAUST | ✅ read | °C (Kelvin×100) |
| 4356–4358 | — | 67–69 | A_CYC_TEMP_OUTSIDE / SUPPLY_CELL / SUPPLY | ✅ read | °C |
| 4361 | 0x1109 | 72 | A_CYC_EXTR_FAN_SPEED | ✅ read | RPM |
| 4362 | 0x110A | 73 | A_CYC_SUPP_FAN_SPEED | ✅ read | RPM |
| 4363 | 0x110B | 74 | A_CYC_RH_VALUE | ✅ read | % |
| 4373–4378 | — | 84–89 | A_CYC_RH_SENSOR_0..5 | ✅ read | 0xFFFF = not present |
| 4379–4384 | — | 90–95 | A_CYC_CO2_SENSOR_0..5 | ✅ read | 0xFFFF = not present |
| 4391–4394 | — | 102–105 | A_CYC_VOC_SENSOR_0..3 | ✅ read | 0xFFFF = not present |
| 4352–4372 (gaps) | — | — | various hardware state | ❌ not read | orientation, UUID, SW version likely here |

### Group: g_cyclone_sw_state — buf 106, reg 4608 (0x1200)

| Reg | Hex | Buf | Register name | Status | Notes |
|---|---|---|---|---|---|
| 4609 | 0x1201 | 107 | A_CYC_STATE | ✅ read/write | operating mode |
| 4610 | 0x1202 | 108 | A_CYC_MODE | ✅ read/write | 0=on, ≠0=off |
| 4611 | 0x1203 | 109 | A_CYC_DEFROSTING | ✅ read | bool |
| 4612 | 0x1204 | 110 | A_CYC_BOOST_TIMER | ✅ read/write | minutes remaining |
| 4613 | 0x1205 | 111 | A_CYC_FIREPLACE_TIMER | ✅ read/write | minutes remaining |
| 4614 | 0x1206 | 112 | A_CYC_EXTRA_TIMER | ✅ read | minutes remaining |
| 4615 | 0x1207 | 113 | A_CYC_WEEKLY_TIMER_ENABLED | ✅ read/write | bool |
| 4616 | 0x1208 | 114 | A_CYC_CELL_STATE | ✅ read | 0=Heat 1=Cool 2=Bypass 3=Defrost |
| 4617 | 0x1209 | 115 | A_CYC_TOTAL_UP_TIME_YEARS | ✅ read | years |
| 4618 | 0x120A | 116 | A_CYC_TOTAL_UP_TIME_HOURS | ✅ read | hours |
| 4619 | 0x120B | 117 | A_CYC_CURRENT_UP_TIME_HOURS | ✅ read | hours |
| 4620 | 0x120C | 118 | A_CYC_REMAINING_TIME_FOR_FILTER | ✅ read | days |
| 4621–4623 | — | 119–121 | — | ❌ not read | unknown |
| 4624 | 0x1210 | 122 | A_CYC_EMERGENCY_STOP_IS_ACTIVATED | ✅ read | bool |
| 4625–4639 | — | 123–137 | — | ❌ not read | unknown |

### Group: g_cyclone_output — buf 138, reg 4864 (0x1300)

| Reg | Hex | Buf | Register name | Status | Notes |
|---|---|---|---|---|---|
| 4870 | 0x1306 | 144 | A_CYC_IO_BYPASS | ✅ read | bypass relay open |
| other | — | — | — | ❌ not read | relay states, etc. |

### Fan speed write registers (legacy protocol, not in response frame)

| Reg (write) | Hex | Register name | Status | Notes |
|---|---|---|---|---|
| — | 0x1550 + offset | AtHome fan speed | ✅ write | special format |
| — | 0x1B50 + offset | Away fan speed | ✅ write | special format |
| — | 0x2150 + offset | Intensive fan speed | ✅ write | special format |
| — | 0x4050 | A_CYC_BOOST_TIME | ✅ write | intensive duration (min) |

### Group: g_cyclone_settings — buf 182, reg 20480 (0x5000)

| Reg | Hex | Buf | Register name | Status | Notes |
|---|---|---|---|---|---|
| 20480 | 0x5000 | 182 | A_CYC_ACTIVATED | ❌ not read | alternative on/off |
| 20481 | 0x5001 | 183 | A_CYC_SUPPLY_HEATING_ADJUST_MODE | ✅ read/write | 0=Supply 1=Extract 2=Extract+ |
| 20482 | 0x5002 | 184 | A_CYC_MIN_SUPPLY_AIR_TEMP | ❌ not read | °C (Kelvin×100) |
| 20483 | 0x5003 | 185 | A_CYC_MAX_SUPPLY_AIR_TEMP | ❌ not read | °C (Kelvin×100) |
| 20484–20486 | 0x5004–0x5006 | 186–188 | — | ❌ not read | unknown |
| 20487 | 0x5007 | 189 | A_CYC_FIREPLACE_EXTR_FAN | ✅ read/write | Individual extract fan % |
| 20488 | 0x5008 | 190 | A_CYC_FIREPLACE_SUPP_FAN | ✅ read/write | Individual supply fan % |
| 20489–20492 | 0x5009–0x500C | 191–194 | — | ❌ not read | unknown |
| 20493 | 0x500D | 195 | A_CYC_EXTRA_AIR_TEMP_TARGET | ✅ read/write | °C |
| 20494 | 0x500E | 196 | A_CYC_EXTRA_EXTR_FAN | ✅ read/write | Extra extract fan % |
| 20495 | 0x500F | 197 | A_CYC_EXTRA_SUPP_FAN | ✅ read/write | Extra supply fan % |
| 20496 | 0x5010 | 198 | A_CYC_EXTRA_TIME | ✅ read/write | Extra duration (min) |
| 20497 | 0x5011 | 199 | A_CYC_FIREPLACE_AIR_TEMP_TARGET | ✅ read/write | Individual °C |
| 20498 | 0x5012 | 200 | — | ❌ not read | unknown |
| 20499 | 0x5013 | 201 | A_CYC_RH_CTRL_ENABLED_HOME | ✅ read/write | bool |
| 20500 | 0x5014 | 202 | A_CYC_CO2_CTRL_ENABLED_HOME | ✅ read/write | bool |
| 20501 | 0x5015 | 203 | — | ❌ not read | unknown |
| 20502 | 0x5016 | 204 | A_CYC_AWAY_AIR_TEMP_TARGET | ✅ read/write | °C |
| 20503 | 0x5017 | 205 | A_CYC_FILTER_REMINDER_DISABLED | ✅ read/write | inverted bool |
| 20504 | 0x5018 | 206 | — | ❌ not read | unknown |
| 20505 | 0x5019 | 207 | A_CYC_RH_CTRL_ENABLED_AWAY | ✅ read/write | bool |
| 20506 | 0x501A | 208 | A_CYC_CO2_CTRL_ENABLED_AWAY | ✅ read/write | bool |
| 20507 | 0x501B | 209 | — | ❌ not read | unknown |
| 20508 | 0x501C | 210 | A_CYC_HOME_AIR_TEMP_TARGET | ✅ read/write | °C |
| 20509–20510 | 0x501D–0x501E | 211–212 | — | ❌ not read | unknown |
| 20511 | 0x501F | 213 | A_CYC_RH_CTRL_ENABLED_BOOST | ✅ read/write | Intensive mode |
| 20512 | 0x5020 | 214 | A_CYC_CO2_CTRL_ENABLED_BOOST | ✅ read/write | Intensive mode |
| 20513 | 0x5021 | 215 | — | ❌ not read | unknown |
| 20514 | 0x5022 | 216 | A_CYC_BOOST_AIR_TEMP_TARGET | ✅ read/write | Intensive °C |
| 20515–20516 | 0x5023–0x5024 | 217–218 | A_CYC_MIN_BYPASS_OUTDOOR/INDOOR_TEMP | ❌ not read | bypass activation thresholds |
| 20517 | 0x5025 | 219 | A_CYC_COOL_HEAT_RECOVERY_ENABLED | ✅ read/write | plug removed confirmation |
| 20518 | 0x5026 | 220 | A_CYC_COOL_HEAT_RECOVERY | ✅ read/write | cool recovery active |
| 20519 | 0x5027 | 221 | — | ❌ not read | unknown |
| 20520 | 0x5028 | 222 | A_CYC_HEAT_EXCHANGER | ✅ read/write | ⚠️ enum values unverified |
| 20521 | 0x5029 | 223 | A_CYC_MAX_CO2 | ✅ read/write | ppm (16-bit) |
| 20522 | 0x502A | 224 | — | ❌ not read | unknown |
| 20523 | 0x502B | 225 | A_CYC_MAX_RH | ✅ read/write | % |
| 20524 | 0x502C | 226 | A_CYC_BYPASS_MAX_OUTDOOR_TEMP | ✅ read/write | °C |
| 20525 | 0x502D | 227 | A_CYC_STEPLESS_BYPASS | ✅ read/write | bool |
| 20526–20527 | 0x502E–0x502F | 228–229 | — | ❌ not read | unknown |
| 20528 | 0x5030 | 230 | A_CYC_BYPASS_SETTING | ✅ read/write | bool |
| 20529–20544 | 0x5031–0x5040 | 231–246 | — | ❌ not read | unknown |
| 20544 | 0x5040 | 246 | A_CYC_BOOST_TIME | ✅ read/write | Intensive duration (min) |
| 20545 | 0x5041 | 247 | A_CYC_FIREPLACE_TIME | ✅ read/write | Individual duration (min) |
| 20546+ | 0x5042+ | 248+ | — | ❌ not read | unknown |

### Filter / calendar registers (special offsets)

| Buf | Register name | Status | Notes |
|---|---|---|---|
| 239 | Filter interval | ✅ read | months |
| 248 | Last filter change day | ✅ read | |
| 249 | Last filter change month | ✅ read | |
| 250 | Last filter change year | ✅ read | +2000 |

---

## Known missing / deferred

The following are confirmed present in the Vallox API register map but not yet implemented:

| Register | Name | Notes |
|---|---|---|
| unknown | Software version | In hw_state range, exact offset unknown |
| unknown | UUID | In hw_state range, exact offset unknown |
| unknown | Device orientation | In hw_state range, exact offset unknown |
| unknown | Humidity mode (Auto/Manual) | In settings range, exact offset unknown |
| 0x5002 | A_CYC_MIN_SUPPLY_AIR_TEMP | Min supply air temperature setting |
| 0x5003 | A_CYC_MAX_SUPPLY_AIR_TEMP | Max supply air temperature setting |
| 0x5023 | A_CYC_MIN_BYPASS_OUTDOOR_TEMP | Lower outdoor temp threshold for bypass |
| 0x5024 | A_CYC_MIN_BYPASS_INDOOR_TEMP | Indoor temp threshold for bypass activation |

---

## Write protocol

```
Frame = length_LE(2) + 0xF900(2) + N×(register_LE(2) + value_LE(2)) + checksum_LE(2)

length   = N×4 + 2
checksum = sum of all 16-bit LE words (length, 0xF900, each reg/val pair) & 0xFFFF
```

Expected success response: `02 00 F5 00 F7 00`
