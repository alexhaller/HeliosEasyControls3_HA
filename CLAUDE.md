# CLAUDE.md — HeliosEasyControls3_HA

## Project overview

This is a Home Assistant HACS custom integration for the **Helios easyControls 3.0** ventilation unit (KWL). Communication with the device uses WebSocket on port 80. The integration is written in Python and follows the Home Assistant component pattern.

- Github project: https://github.com/alexhaller/HeliosEasyControls3_HA
- Project forked from: https://github.com/frawe/EasyControls3_homeassistant

Key files:
- [EasyControls3Instance.py](custom_components/HeliosEasyControls3_HA/EasyControls3Instance.py) — WebSocket client; parses raw binary frames from the device. Do not change the WebSocket binary frame format without also updating the parser in `EasyControls3Instance._parseData`.
- [__init__.py](custom_components/HeliosEasyControls3_HA/__init__.py) — HA entry point; sets up the `DataUpdateCoordinator` with a 60 s poll interval
- [config_flow.py](custom_components/HeliosEasyControls3_HA/config_flow.py) — UI config flow (only needs IP address)
- [const.py](custom_components/HeliosEasyControls3_HA/const.py) — shared constants (`DOMAIN`, etc.)
- [KWLStates.py](custom_components/HeliosEasyControls3_HA/KWLStates.py) — enum for KWL operating modes
- Platform modules: `sensor.py`, `number.py`, `select.py`, `switch.py`, `time.py`

## Register mapping — never guess, always verify

Every register address must be justified by the unit's own firmware, not by
reverse engineering from behaviour. The device's web UI ships the complete
register table in clear text.

- **The table is in the repo**: [docs/registers.json](docs/registers.json), ~870
  `VlxDevConstants` entries. Regenerate with
  `python scripts/extract_registers.py <device-ip>`. Look up any address there
  *before* using it; if the firmware name does not describe the setting you
  want, the address is wrong.
- **The UI bindings are in the same bundle** (`http://<device-ip>/js/bundle.js`,
  gzip-encoded). Searching for `modbus:VlxDevConstants.<NAME>` yields the control
  definition with its value list and any inversion — e.g. `A_CYC_COOLRECOVERY_DISABLED`
  and `A_CYC_BYPASS_LOCKED` are both inverted, and `list_helios` / `helioslist`
  override the generic value list on Helios units.
- **Then round-trip it against the device**: write a changed value, confirm the
  mapped read offset picks up exactly that value *and* that the unit's own web UI
  reflects the change, then restore the original. A write that is acknowledged
  proves only that the address exists — not that it is the right setting.

Do not record a mapping as verified on the strength of a UI reading alone.
Registers that merely happened to be written at the same time as a UI observation
have produced wrong mappings here before: the Temperature Control Mode was pointed
at `A_CYC_USED_SETTINGS_VARIABLES` (0x5001), and the Bypass, Stepless Bypass,
Cool Recovery and Heat Exchanger switches wrote into defrost parameters and I/O
configuration registers.

A rejected write is silent — the device just omits the `02 00 F5 00 F7 00`
acknowledgement. `_check_write_response` raises `WriteRejected` for this; never
downgrade that back to a log line.

## Project-specific notes

- **pip-audit** domain for this project is `HeliosEasyControls3_HA`; the only listed requirement is `python-dateutil` (`websockets` is bundled by HA core and deliberately not listed).
- **Brand assets**: `custom_components/HeliosEasyControls3_HA/brand/icon.png` and `brands/icon.png` (Helios red #C62828, 512×512 PNG).
