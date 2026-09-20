# Helios easyControls 3.0 — Home Assistant Integration

HACS custom integration for the **Helios KWL easyControls 3.0** ventilation unit. Communication uses the WebSocket protocol on port 80.

## Installation

1. Add via HACS as a custom repository
2. After restart, search for **Helios easyControls 3.0** in the integration setup
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
| Bypass Status | Binary: bypass relay state |

### Sensors (diagnostic)
| Entity | Description |
|---|---|
| Last / Next Filter Change | Dates |
| Filter Remaining Days | Days until filter change due |
| Total Uptime Years / Hours | Cumulative device runtime |
| Current Uptime Hours | Runtime since last restart |
| External RH Sensor Count | Number of connected external RH sensors |
| CO2 Sensor Count | Number of connected CO2 sensors |
| VOC Sensor Count | Number of connected VOC sensors |

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
| CO2 Control Home / Away / Intensive | Switch | Enable CO2-driven fan speed (only shown if CO2 sensor present) |
| RH Limit | Number (%) | Global humidity threshold |
| CO2/VOC Limit | Number (ppm) | Global CO2/VOC threshold |
| Intensive Mode Duration | Time | Duration for boost mode timer |
| Extra Mode Duration | Time | Duration for extra mode timer |
| Individual Mode Duration | Time | Duration for individual mode timer |
| Weekly Timer | Switch | Enable weekly schedule program |
| Filter Reminder | Switch | Enable filter change reminder |
| Temperature Control Mode | Select | Supply / Extract / Extract+ (Zuluft / Abluft / Abluft Plus) |
| Heat Exchanger | Select | Plastic / Enthalpy (cell type) |
| Bypass | Switch | Manual bypass enable |
| Stepless Bypass | Switch | Stepless (partial) bypass enable |
| Cool Recovery | Switch | Activate cool recovery mode |

---

## Register Map

### Protocol overview

The device uses a proprietary WebSocket binary protocol. A single request (`03 00 F6 00 00 00 F9 00`) returns all data in one frame. Writes use `F9 00` frames with register/value pairs.

**Buffer offset formula**: `buf_offset = group_buf_start + (register − group_reg_start)`  
**Read**: `data[buf_offset × 2]` (high byte), `data[buf_offset × 2 + 1]` (low byte)  
**Temperature encoding**: `kelvin × 100 = round((celsius + 273.15) × 100)`

#### Frame layout — derived from the firmware, not guessed

The web UI bundle defines the reply's structure outright, as
`RANGE_START_<group>` / `RANGE_END_<group>` constants plus `vlxBufferSize=705`,
which matches the observed frame byte-for-byte. The reply is those ranges
concatenated in declaration order:

| Group | Registers | Buf | Words |
|---|---|---|---|
| g_cyclone_general_info | 0–35 | 0–35 | 36 |
| g_typhoon_general_info | 256–282 | 36–62 | 27 |
| g_cyclone_hw_state | 4352–4394 | 63–105 | 43 |
| g_cyclone_sw_state | 4608–4632 | 106–130 | 25 |
| g_cyclone_time | 4848–4854 | 131–137 | 7 |
| g_cyclone_output | 4864–4870 | 138–144 | 7 |
| g_cyclone_input | 5120–5126 | 145–151 | 7 |
| g_cyclone_config | 8192–8221 | 152–181 | 30 |
| g_cyclone_settings | 20480–20555 | 182–257 | 76 |
| g_typhoon_settings | 21760–21782 | 258–280 | 23 |
| g_constant_flow | 32768–32783 | 281–296 | 16 |
| g_faults | 36864–37063 | 297–496 | 200 |
| g_cyclone_weekly_schedule | 40960–41128 | 497–665 | 169 |
| g_cyclone_extended | 46000–46038 | 666–704 | 39 |

Two properties of this layout matter when adding registers:

1. **Each range opens with a length marker.** The word at a range's nominal
   start register (always an unnamed address such as 36864 or 40960) holds that
   range's word count, so the first real value sits at `buf_start + 1`. Reading
   `A_CYC_TOTAL_FAULT_COUNT` at the fault range's start yields 200 — the range
   length, not a fault count.
2. **Ranges for absent hardware are omitted.** `g_tornado_0` / `g_tornado_1`
   (45056–45088 / 45216–45248) are declared but missing from this unit's reply,
   because `A_CYC_TOR_0_CONNECTED` is 0 — no post-heater module. On a unit that
   has one, everything after the weekly schedule shifts by 66 words. Anything
   past the schedule must therefore resolve its offset by walking the length
   markers rather than hardcoding a position; `_find_extended_start()` does this.

`g_cyclone_hurricane` (46100–46113) is declared but is *not* part of the reply
at all. Its registers are reachable only through the second request type below.

#### Second request type: reading individual registers

`WS_WEB_UI_COMMAND_READ_DATA` (250) takes a list of addresses instead of
dumping the tables, which reaches registers outside the reply frame. The frame
is built exactly like a write, with a stride of one word per item:

```
length_LE(2) + 0xFA00(2) + N×address_LE(2) + checksum_LE(2)
length   = N + 2
checksum = sum of all 16-bit LE words & 0xFFFF
```

The reply comes back as `length + 0xF900 + N×(address, value) + checksum` —
address/value pairs, so each value is self-identifying. Verified by requesting
known registers alongside unknown ones and confirming the known values.

**Write frame format**:
```
length_LE(2) + 0xF900(2) + N×(register_LE(2) + value_LE(2)) + checksum_LE(2)
length   = N×4 + 2
checksum = sum of all 16-bit LE words & 0xFFFF
```
Expected success response: `02 00 F5 00 F7 00`

**Important**: The **general info, hardware state, software state and output** register ranges (0x0001–0x12F6) are shared with the open-source Vallox WebSocket API. The **settings range (0x5000+) differs from the public Vallox layout** in places, so the addresses below come from the unit's own firmware rather than from the Vallox API.

Full Vallox API register reference: https://github.com/yozik04/vallox_websocket_api

---

### How the register mapping was obtained

The authoritative source is the unit itself. Its web UI ships the complete register
table in clear text, so nothing here needs to be guessed:

1. **Fetch the web UI's bundle.** `http://<device-ip>/js/bundle.js` is served
   gzip-encoded — decompress it before searching. It contains ~870
   `VlxDevConstants.<NAME>=<address>` assignments, 727 of them `A_CYC_*`.
   The extracted table is checked in as [`docs/registers.json`](docs/registers.json)
   and regenerated with [`scripts/extract_registers.py`](scripts/extract_registers.py).
2. **Find how a control binds to a register.** The same bundle defines the UI
   itself, e.g. `coolrecovery:{…data:{value:1,modbus:VlxDevConstants.A_CYC_COOLRECOVERY_DISABLED},list:[{txt:"select_option_off",data:{value:1}},{txt:"select_option_on",data:{value:0}}]}`.
   This gives the register, the value list *and* any inversion — the three things
   that are impossible to infer reliably from behaviour alone. Entries named
   `list_helios` / `helioslist` override `list` on Helios-branded units.
3. **Confirm the read offset.** Apply the buffer-offset formula, then check that
   the value at that offset matches what the UI displays.
4. **Round-trip against the device.** Write a changed value, confirm the mapped
   read offset picks up exactly that value *and* that the unit's own web UI
   reflects the change, then restore the original.

Step 4 is what separates a verified mapping from a plausible one. Several bugs in
this integration came from correlating a UI reading with a register that was
merely being written at the same time. A register that acknowledges a write proves
only that the address exists — not that it is the setting you think it is. Both
the firmware name and a UI round-trip have to agree before a mapping is recorded
as verified here.

A rejected write is silently dropped: the device simply does not send the
`02 00 F5 00 F7 00` acknowledgement. Treat a missing ACK as a wrong register or an
out-of-range value, never as success.

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
| 4357 | 0x1105 | 68 | A_CYC_TEMP_SUPPLY_CELL_AIR | ❌ not read | Identical to supply air on KWL 360 W ET |
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
| 4391–4394 | 0x1127–0x112A | 102–105 | A_CYC_VOC_SENSOR_0..3 | ✅ read | External VOC sensors (0xFFFF or 0 = absent) |

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

### Group: Time — buf 131, reg 4848 (0x12F0)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 4848 | 0x12F0 | 131 | — | — | Range length marker (7) |
| 4849–4854 | 0x12F1–0x12F6 | 132–137 | A_CYC_MINUTE / HOUR / DAY / MONTH / YEAR / WEEKDAY | ❌ not read | Device clock; year is offset from 2000. Decodes correctly against wall-clock time — usable for drift detection |

---

### Group: Digital Outputs — buf 138, reg 4864 (0x1300)

> buf = 138 + (reg − 4864)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 4864 | 0x1300 | 138 | — | — | Range length marker (7) |
| 4865 | 0x1301 | 139 | A_CYC_IO_EXTRACT_FAN | ✅ read | **Drive level, not a relay state** — observed 135 while the extract fan ran at 1395 rpm |
| 4866 | 0x1302 | 140 | A_CYC_IO_SUPPLY_FAN | ✅ read | Drive level; observed 158 at 1638 rpm, tracking the higher supply speed |
| 4867 | 0x1303 | 141 | A_CYC_IO_ERROR | ✅ read | bool: error output |
| 4868 | 0x1304 | 142 | A_CYC_IO_HEATER | ✅ read | bool: heater output |
| 4869 | 0x1305 | 143 | A_CYC_IO_EXTRA_HEATER | ✅ read | bool: extra heater output |
| 4870 | 0x1306 | 144 | A_CYC_IO_BYPASS | ✅ read | Bypass relay state (= BypassOpen) |

---

### Group: Digital Inputs — buf 145, reg 5120 (0x1400)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 5120 | 0x1400 | 145 | — | — | Range length marker (7) |
| 5121–5126 | 0x1401–0x1406 | 146–151 | A_CYC_IN_EXTRACT_FAN / SUPPLY_FAN / ERROR / HEATER / EXTRA_HEATER / BYPASS | ❌ not read | Input states. `IN_ERROR` reads 1 with no fault present, so the polarity is not plain active-high — do not surface it as a problem flag without clarifying that first |

---

### Group: Configuration — buf 152, reg 8192 (0x2000)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 8192 | 0x2000 | 152 | — | — | Range length marker (30) |
| 8194–8195 | 0x2002–0x2003 | 154–155 | A_CYC_GW_ADDRESS_1..2 | ❌ not read | Gateway IP, two octets per word |
| 8196–8197 | 0x2004–0x2005 | 156–157 | A_CYC_MASK_ADDRESS_1..2 | ❌ not read | Subnet mask |
| 8198–8207 | 0x2006–0x200F | 158–167 | A_CYC_HELIOS_*_TUNING | ❌ not read | Helios-specific DIBT/PHI tuning constants |
| 8211 | 0x2013 | 171 | A_CYC_ETH_CLOUD_ENABLED | ❌ not read | Cloud / Ethernet enabled |
| 8212–8213 | 0x2014–0x2015 | 172–173 | A_CYC_IP_ADDRESS_1..2 | ❌ not read | Device IP address |
| 8214–8221 | 0x2016–0x201D | 174–181 | A_CYC_UUID0..7 | ❌ not read | Device UUID (8 words) |

The address encoding packs two octets per word: 49320 = 0xC0A8 = `192.168`,
382 = 0x017E = `1.126`. Decoding the block reproduced the unit's actual IP,
gateway and mask, which is what confirms these offsets.

---

### Group: Settings — buf 182, reg 20480 (0x5000) — **Helios-specific layout**

> ℹ️ Register names come from the unit's own firmware — see [How the register mapping was obtained](#how-the-register-mapping-was-obtained). The full table is in [`docs/registers.json`](docs/registers.json).

> ℹ️ **Profile block layout**: each profile occupies four consecutive registers — RH control, CO2 control, fan speed, air temp target — at a stride of 6: Away at 0x5013, Home at 0x5019, Intensive at 0x501F.

| Reg | Hex | Buf | Name (Helios-specific) | Status | Notes |
|---|---|---|---|---|---|
| 20480 | 0x5000 | 182 | — | — | Range length marker (76) |
| 20481 | 0x5001 | 183 | A_CYC_USED_SETTINGS_VARIABLES | ❌ not read | **Not** the temperature control mode — that is 0x5045 |
| 20482 | 0x5002 | 184 | A_CYC_MODBUS_ADDRESS | ❌ not read | RTU slave address (UI range 1–247) |
| 20483 | 0x5003 | 185 | A_CYC_MODBUS_BAUD_X100 | ❌ not read | Baud ÷ 100 — reads 192, i.e. 19200 baud |
| 20484 | 0x5004 | 186 | A_CYC_MODBUS_FRAME | ❌ not read | RTU framing |
| 20485 | 0x5005 | 187 | A_CYC_EXTR_FAN_BALANCE_BASE | ✅ read/write | Extract side of the fan balance |
| 20486 | 0x5006 | 188 | A_CYC_SUPP_FAN_BALANCE_BASE | ✅ read/write | Supply side of the fan balance |
| 20487 | 0x5007 | 189 | A_CYC_FIREPLACE_EXTR_FAN | ✅ read/write | Individual extract fan % |
| 20488 | 0x5008 | 190 | A_CYC_FIREPLACE_SUPP_FAN | ✅ read/write | Individual supply fan % |
| 20489 | 0x5009 | 191 | A_CYC_PARTIAL_BYPASS_DISABLED | ❌ not read | Partial bypass disabled flag |
| 20490 | 0x500A | 192 | A_CYC_RH_BASIC_LEVEL | ✅ read/write | RH Limit % |
| 20491 | 0x500B | 193 | A_CYC_CO2_THRESHOLD | ✅ read/write | CO2/VOC Limit ppm |
| 20492 | 0x500C | 194 | A_CYC_EXTRA_ENABLED | ✅ read/write | Extra mode enabled. Round-trip verified, but the register has **no binding in the web UI**, so the UI cross-check could not be performed |
| 20493 | 0x500D | 195 | A_CYC_EXTRA_AIR_TEMP_TARGET | ✅ read/write | Extra air temp target (°C) |
| 20494 | 0x500E | 196 | A_CYC_EXTRA_EXTR_FAN | ✅ read/write | Extra extract fan % |
| 20495 | 0x500F | 197 | A_CYC_EXTRA_SUPP_FAN | ✅ read/write | Extra supply fan % |
| 20496 | 0x5010 | 198 | A_CYC_EXTRA_TIME | ✅ read/write | Extra mode duration (min) |
| 20497 | 0x5011 | 199 | A_CYC_FIREPLACE_AIR_TEMP_TARGET | ✅ read/write | Individual air temp target (°C) |
| 20498 | 0x5012 | 200 | A_CYC_CF_FAN_SPEED_UNIT | ❌ not read | Fan speed unit; 2 = percent (constant-flow regulation off) |
| 20499 | 0x5013 | 201 | A_CYC_AWAY_RH_CTRL_ENABLED | ✅ read/write | Away RH control (verified) |
| 20500 | 0x5014 | 202 | A_CYC_AWAY_CO2_CTRL_ENABLED | ✅ read/write | Away CO2 control |
| 20501 | 0x5015 | 203 | A_CYC_AWAY_SPEED_SETTING | ✅ read | Away fan speed % |
| 20502 | 0x5016 | 204 | A_CYC_AWAY_AIR_TEMP_TARGET | ✅ read/write | Away air temp target (°C) |
| 20503 | 0x5017 | 205 | A_CYC_FILTER_REMINDER_DISABLED | ✅ read/write | Inverted: 1=reminder off |
| 20504 | 0x5018 | 206 | A_CYC_FILTER_REMINDER_AUTOMATIC_TIME | ✅ read/write | Automatic filter reminder interval (UI default 14; no UI min/max, entity uses a permissive 1–365) |
| 20505 | 0x5019 | 207 | A_CYC_HOME_RH_CTRL_ENABLED | ✅ read/write | Home RH control (verified) |
| 20506 | 0x501A | 208 | A_CYC_HOME_CO2_CTRL_ENABLED | ✅ read/write | Home CO2 control |
| 20507 | 0x501B | 209 | A_CYC_HOME_SPEED_SETTING | ✅ read | AtHome fan speed % |
| 20508 | 0x501C | 210 | A_CYC_HOME_AIR_TEMP_TARGET | ✅ read/write | Home air temp target (°C) |
| 20509 | 0x501D | 211 | A_CYC_DEFROST_RPM_LIMIT | ❌ not read | Defrost fan speed limit |
| 20510 | 0x501E | 212 | A_CYC_MAX_FANSPEED_SCALING_EXTRACT | ✅ read/write | Max extract fan scaling (no UI min/max; entity clamps 1–100) |
| 20511 | 0x501F | 213 | A_CYC_BOOST_RH_CTRL_ENABLED | ✅ read/write | Intensive RH control |
| 20512 | 0x5020 | 214 | A_CYC_BOOST_CO2_CTRL_ENABLED | ✅ read/write | Intensive CO2 control |
| 20513 | 0x5021 | 215 | A_CYC_BOOST_SPEED_SETTING | ✅ read | Intensive fan speed % |
| 20514 | 0x5022 | 216 | A_CYC_BOOST_AIR_TEMP_TARGET | ✅ read/write | Intensive air temp target (°C) |
| 20515 | 0x5023 | 217 | A_CYC_MAX_FANSPEED_SCALING_SUPPLY | ✅ read/write | Max supply fan scaling (no UI min/max; entity clamps 1–100) |
| 20516 | 0x5024 | 218 | A_CYC_COOLRECOVERY_DISABLED | ✅ read/write | Cool Recovery switch — **inverted** (1 = off) |
| 20517 | 0x5025 | 219 | A_CYC_RELAY_MODE | ❌ not read | Relay configuration — do not write |
| 20518 | 0x5026 | 220 | A_CYC_DIGITAL_INPUT_1_MODE | ❌ not read | Digital input configuration — do not write |
| 20519 | 0x5027 | 221 | A_CYC_DIGITAL_INPUT_2_MODE | ❌ not read | Digital input configuration — do not write |
| 20520 | 0x5028 | 222 | A_CYC_ANALOG_INPUT_MODE | ❌ not read | Analog input configuration — do not write |
| 20521 | 0x5029 | 223 | A_CYC_MLV_SUPPLY_LOWER_LIMIT | ✅ read/write | **Was mislabelled `A_CYC_DEFROST_TEMP_LIMIT` here.** MLV supply lower limit, UI range 12–25 °C; decodes to a clean 18.0 °C and accepts writes |
| 20522 | 0x502A | 224 | A_CYC_SUPPLY_AIR_DEFROST_TEMP | ✅ read/write | Supply air defrost temperature, UI range 12–20 °C |
| 20523 | 0x502B | 225 | A_CYC_MLV_AUTO_MANUAL | ❌ not read | **Was mislabelled `A_CYC_DEFROST_HYSTERESIS` here.** MLV function: 0=automatic, 1=manual |
| 20524 | 0x502C | 226 | A_CYC_DEFROST_MODE | ❌ not read | 0=bypass, 1=fan stop — do not write |
| 20525 | 0x502D | 227 | A_CYC_DEFROST_RH_PARAM | ❌ not read | Defrost parameter — do not write |
| 20526 | 0x502E | 228 | A_CYC_DEFROST_TEMP_PARAM | ❌ not read | Defrost parameter — do not write |
| 20527 | 0x502F | 229 | A_CYC_DEFROST_EXH_OFFSET | ❌ not read | Defrost parameter — do not write |
| 20528 | 0x5030 | 230 | A_CYC_DEFROST_COMP_LIMIT | ❌ not read | Defrost parameter — rejects writes |
| 20529 | 0x5031 | 231 | A_CYC_MLV_SUMMER_SETPOINT | ✅ read/write | UI range 12–25 °C |
| 20530 | 0x5032 | 232 | A_CYC_MLV_MODES | ❌ not read | 0=both, 1=preheating, 2=cooling |
| 20531 | 0x5033 | 233 | A_CYC_MLV_WINTER_SETPOINT | ✅ read/write | UI range −10–5 °C |
| 20532–20533 | 0x5034–0x5035 | 234–235 | A_CYC_MLV_SUMMER_/WINTER_HYSTERESIS | ❌ not read | — |
| 20534 | 0x5036 | 236 | A_CYC_WATERHEATER_STORED_I | ❌ not read | PID integral store, not a temperature |
| 20535 | 0x5037 | 237 | A_CYC_INSTALLATION_DONE | ❌ not read | Commissioning flag — do not write |
| 20536 | 0x5038 | 238 | A_CYC_DEFROST_RH_OFFSET | ❌ not read | Defrost parameter — do not write |
| 20537 | 0x5039 | 239 | A_CYC_FILTER_CHANGE_INTERVAL | ✅ read | Filter interval in **days** (180 = the UI's "6 months") |
| 20538 | 0x503A | 240 | A_CYC_CELL_TYPE | ✅ read/write | Heat Exchanger select — 0=aluminium (not on Helios) 1=plastic 2=enthalpy |
| 20539–20542 | 0x503B–0x503E | 241–244 | A_CYC_EXTRA_HEATER_TYPE / POST_HEATER_TYPE / BRANDING / SIDEDNESS | ❌ not read | — |
| 20543 | 0x503F | 245 | A_CYC_RH_LEVEL_MODE | ✅ read/write | Humidity mode: 0=automatic, 1=manual |
| 20544 | 0x5040 | 246 | A_CYC_BOOST_TIME | ✅ read/write | Intensive mode duration (min) |
| 20545 | 0x5041 | 247 | A_CYC_FIREPLACE_TIME | ✅ read/write | Individual mode duration (min) |
| 20546 | 0x5042 | 248 | A_CYC_FILTER_CHANGED_DAY | ✅ read | Last filter change day |
| 20547 | 0x5043 | 249 | A_CYC_FILTER_CHANGED_MONTH | ✅ read | Last filter change month |
| 20548 | 0x5044 | 250 | A_CYC_FILTER_CHANGED_YEAR | ✅ read | Last filter change year (+2000) |
| 20549 | 0x5045 | 251 | A_CYC_SUPPLY_HEATING_ADJUST_MODE | ✅ read/write | Temperature Control Mode — 0=supply air 1=extract air 2=cooling mode |
| 20550 | 0x5046 | 252 | A_CYC_MIN_DEFROST_TIME | ❌ not read | — |
| 20551 | 0x5047 | 253 | A_CYC_PARTIAL_BYPASS | ✅ read/write | Stepless Bypass switch (Helios: 0=off 1=on) |
| 20552 | 0x5048 | 254 | A_CYC_BYPASS_LOCKED | ✅ read/write | Bypass switch — **inverted** (1 = off) |
| 20553 | 0x5049 | 255 | A_CYC_OPT_TEMP_SENSOR_MODE | ❌ not read | 0=none, 1=MLV, 2=air heater, 3=supply |
| 20554 | 0x504A | 256 | A_CYC_POST_HEATER_WINTER_SETPOINT | ✅ read/write | UI range 0–19 °C |
| 20555 | 0x504B | 257 | A_CYC_DEWPOINT_LIMIT_IN_USE | ❌ not read | — |

---

### Typhoon Settings — buf 258, reg 21760 (0x5500)

> ⚠️ **This range carries credentials in clear text.** `A_CYC_ACCESS_PASSWORD`
> (buf 260) and `A_CYC_USER_PASSWORD` (buf 261) are part of every reply. Never
> expose them as entities or attributes, and redact them from any log or
> diagnostics dump.

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 21760 | 0x5500 | 258 | — | — | Range length marker (23) |
| 21761 | 0x5501 | 259 | A_CYC_LANGUAGE | ❌ not read | Display language |
| 21762–21763 | 0x5502–0x5503 | 260–261 | A_CYC_ACCESS_PASSWORD / USER_PASSWORD | 🚫 never expose | See warning above |
| 21764–21765 | 0x5504–0x5505 | 262–263 | A_CYC_ACCESS_LEVEL / PARENTAL_CTRL_ENABLED | ❌ not read | — |
| 21766 | 0x5506 | 264 | A_CYC_BOOST_TIMER_ENABLED | ❌ not read | Boost timer enable |
| 21767 | 0x5507 | 265 | A_CYC_FIREPLACE_TIMER_ENABLED | ❌ not read | Individual timer enable |
| 21768–21771 | 0x5508–0x550B | 266–269 | A_CYC_SUMMER_TIME_AUTO_ENAB / 12_HOUR_CLOCK / SLEEP_DELAY / BG_LIGHT_LEVEL | ❌ not read | Panel settings |
| 21772 | 0x550C | 270 | A_CYC_EXTRA_TIMER_ENABLED | ❌ not read | Extra timer enable |
| 21773 | 0x550D | 271 | A_CYC_UPDATE_STATUS | ❌ not read | — |

---

### Constant Flow — buf 281, reg 32768 (0x8000)

| Reg | Hex | Buf | Name | Status | Notes |
|---|---|---|---|---|---|
| 32768 | 0x8000 | 281 | — | — | Range length marker (16) |
| 32769–32774 | 0x8001–0x8006 | 282–287 | A_CYC_CF_{AWAY,HOME,BOOST}_{SUPPLY,EXTRACT}_BASE_AIRFLOW | ✅ read/write | Per-profile base airflow; reads 30/30, 50/50, 70/70. No UI min/max, entities use a permissive 0–300 |
| 32775–32776 | 0x8007–0x8008 | 288–289 | A_CYC_MAX_TEST / DUCT_TEST | ❌ not read | Commissioning tests — do not write |
| 32777–32778 | 0x8009–0x800A | 290–291 | A_CYC_MEASURED_SUPPLY / MEASURED_EXTRACT | ✅ read | Measured airflow; 0 while regulation runs in percent mode |
| 32779–32780 | 0x800B–0x800C | 292–293 | A_CYC_CF_LIMITER / CF_LIMITER_ACTIVE | ✅ read | Limiter state |
| 32781–32782 | 0x800D–0x800E | 294–295 | A_CYC_CF_SUPPLY_/EXTRACT_FANLOAD_LEVEL | ✅ read | Fan load levels |

---

### Extended — buf 666, reg 46000 (0xB3B0)

> Position shifts when a post-heater module is fitted; resolve it via the range
> length markers, never by hardcoding 666.

| Reg | Hex | Offset | Name | Status | Notes |
|---|---|---|---|---|---|
| 46000 | 0xB3B0 | +0 | — | — | Range length marker (39) |
| 46001–46002 | 0xB3B1–0xB3B2 | +1..+2 | A_CYC_CONDENSATION_PREVENTION / _METHOD | ✅ read | — |
| 46003–46004 | 0xB3B3–0xB3B4 | +3..+4 | A_CYC_SUPPLY_/EXTRACT_AIRFLOW | ✅ read | 0 in percent mode |
| 46009 | 0xB3B9 | +9 | A_CYC_TOR_0_CONNECTED | ✅ read | 0 here — this is why the tornado ranges are absent from the reply |
| 46014 | 0xB3BE | +14 | A_CYC_CF_FAN_SPEED | ✅ read | — |
| 46021 | 0xB3C5 | +21 | A_CYC_TIMED_FUNCTION_ENABLED | ✅ read/write | Holiday function on/off |
| 46022–46024 | 0xB3C6–0xB3C8 | +22..+24 | A_CYC_TIMED_FUNCTION_START_DAY / MONTH / YEAR | ✅ read/write | Year offset from 2000; written as one frame so the date stays consistent |
| 46025–46027 | 0xB3C9–0xB3CB | +25..+27 | A_CYC_TIMED_FUNCTION_END_DAY / MONTH / YEAR | ✅ read/write | As above |
| 46028 | 0xB3CC | +28 | A_CYC_TIMED_FUNCTION_MODE | ✅ read/write | 0=at home, 1=away, 2=standby |
| 46029 | 0xB3CD | +29 | A_CYC_TIMED_FUNCTION_RETURN_MODE | ✅ read | No UI binding, so the value list is unknown — exposed read-only |
| 46031–46033 | 0xB3CF–0xB3D1 | +31..+33 | A_CYC_CONSTANT_FAN_MAX / MIN / BALANCE | ✅ read | 200 / 30 / 100 |
| 46034 | 0xB3D2 | +34 | A_CYC_CONSTANT_AIRFLOW_ALERT | ✅ read | — |

---

### Hurricane — reg 46100–46113 (0xB414–0xB421), **not in the reply frame**

Reachable only through a `READ_DATA` request. Probed read-only with known
registers alongside for control:

| Reg | Name | Value | Notes |
|---|---|---|---|
| 46101–46102 | A_CYC_MAX_CF_SCALING_SUPPLY / EXTRACT | 222 / 222 | — |
| 46103–46104 | A_CYC_CONSTANT_FAN_P_FACTOR / CF_FUNCTION_CALL_TIME | 5 / 5000 | — |
| 46105–46106 | A_CYC_CF_BLOCKAGE_RATIO_SUPPLY / EXTRACT | 400 / 400 | — |
| 46107–46108 | A_CYC_SUPPLY_/EXTRACT_FILTER_DIRTINESS_INDEX | **0 / 0** | See below |
| 46109–46113 | A_CYC_CF_RECOVERY_* / CF_DUCTCYCLE_* | 0 / 55 / 55 / 0 / 0 | — |

**Filter dirtiness index — deliberately not implemented.** Both indices read 0
while neighbouring registers in the same block return real values, so the
request is not at fault. The index is produced by the constant-flow algorithm,
which is not running on this unit: `A_CYC_CF_FAN_SPEED_UNIT` is 2 (percent
regulation), `A_CYC_MEASURED_SUPPLY`/`EXTRACT` are 0 and
`A_CYC_CF_LIMITER_ACTIVE` is 0. It would stay 0 until the unit is commissioned
for constant-flow regulation, which changes how the whole machine regulates and
is not a side effect an integration feature should carry. If that switch is ever
made, add it behind a slow second poll — the index moves over weeks.

---

### Faults — buf 297, reg 36864 (0x9000)

| Reg | Hex | Buf | Name | Status |
|---|---|---|---|---|
| 36864 | 0x9000 | 297 | — | Range length marker (200) |
| 36865 | 0x9001 | 298 | A_CYC_TOTAL_FAULT_COUNT | ❌ not read |
| 36866+ | 0x9002+ | 299+ | A_CYC_FAULT_CODE, SEVERITY, FIRST_DATE, LAST_DATE, COUNT, ACTIVITY (×33) | ❌ not read |

The whole range reads zero on this unit, so a decode cannot be validated until
a fault actually occurs.

---

### Weekly Schedule — buf 497, reg 40960 (0xA000)

168 entries (7 days × 24 hours) at buf 498–665, one word per hour, holding a
profile value. Monday 00:00 is buf 498; `buf = 498 + day × 24 + hour`.

| Status | Notes |
|---|---|
| ❌ not read/written | Present in every reply, so no protocol work would be needed |

---

## Implementable next (known registers, just not coded yet)

| Register(s) | Name | Where |
|---|---|---|
| buf 1–10 (reg 1–10) | Application SW version | General info |
| buf 26 (reg 26) | Device orientation (A_CYC_NO_HANDEDNESS) | General info |
| buf 132–137 | Device clock — drift detection against HA's time | Time |
| buf 146–151 | Digital input states (clarify `IN_ERROR` polarity first) | Input |
| buf 154–181 | IP / gateway / mask / cloud-enabled as diagnostics | Configuration |
| buf 298+ | Fault history | Faults |
| buf 498–665 | Full weekly schedule (168 hourly slots) | Weekly schedule |

> An earlier revision of this table listed the IO outputs at **buf 144–148**.
> That was wrong: buf 144 is `A_CYC_IO_BYPASS`, which the integration already
> read. The outputs are at **buf 139–143**, and implementing from the old figure
> would have shifted every one of them by five words.

## Pending verification

| Item | Action needed |
|---|---|
| Newly writable settings registers | Round-trips were verified at register level — write, read back the exact value, restore — but the web UI was not observed during the change. Spot-check fan balance and the post-heater winter setpoint in the unit's own UI to complete step 4 of the methodology |
| `A_CYC_EXTRA_ENABLED` (0x500C) | Writable and clearly named, but has no binding anywhere in the web UI bundle, so its effect could not be cross-checked |
| `A_CYC_TIMED_FUNCTION_RETURN_MODE` (46029) | No UI binding, so the value list is unknown; exposed read-only until it is |
| Fan balance, max fan speed scaling, CF base airflow bounds | No min/max in the UI bundle; entity limits are permissive placeholders, not firmware limits |
| `A_CYC_IN_ERROR` (buf 148) | Reads 1 with no fault present — determine the polarity before surfacing it |
