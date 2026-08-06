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

## Project-specific notes

- **pip-audit** domain for this project is `HeliosEasyControls3_HA`; the only listed requirement is `python-dateutil` (`websockets` is bundled by HA core and deliberately not listed).
- **Brand assets**: `custom_components/HeliosEasyControls3_HA/brand/icon.png` and `brands/icon.png` (Helios red #C62828, 512×512 PNG).
