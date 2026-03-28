# CLAUDE.md — HeliosEasyControls3_HA

## Project overview

This is a Home Assistant HACS custom integration for the **Helios easyControls 3.0** ventilation unit (KWL). Communication with the device uses WebSocket on port 80. The integration is written in Python and follows the Home Assistant component pattern.

Key files:
- [EasyControls3Instance.py](custom_components/HeliosEasyControls3_HA/EasyControls3Instance.py) — WebSocket client; parses raw binary frames from the device
- [__init__.py](custom_components/HeliosEasyControls3_HA/__init__.py) — HA entry point; sets up the `DataUpdateCoordinator` with a 60 s poll interval
- [config_flow.py](custom_components/HeliosEasyControls3_HA/config_flow.py) — UI config flow (only needs IP address)
- [const.py](custom_components/HeliosEasyControls3_HA/const.py) — shared constants (`DOMAIN`, etc.)
- [KWLStates.py](custom_components/HeliosEasyControls3_HA/KWLStates.py) — enum for KWL operating modes
- Platform modules: `sensor.py`, `number.py`, `select.py`, `switch.py`, `time.py`

## Code Quality
- Always check Python code with:
-- `ruff check .` — linting
-- `mypy custom_components/` — static type checking
- Fix all reported issues before considering a change complete.
- Always check for latest releases of required packages

## Development conventions

- **Python 3.9+** (mypy is configured for 3.9).
- All async I/O goes through `EasyControls3Instance`; platform entities only read from the coordinator snapshot.
- Keep entity unique IDs tied to the device serial number so they survive IP changes.
- Follow existing HA patterns: `CoordinatorEntity`, `async_setup_entry`, `async_unload_entry`.

## Code quality

- Do not add error handling for conditions that cannot occur given HA's coordinator guarantees.

## What to avoid

- Do not change the WebSocket binary frame format without also updating the parser in `EasyControls3Instance._parseData`.
- Do not introduce synchronous I/O inside async methods.
- Do not add features, refactors, or "improvements" beyond what is explicitly requested.
- Do not add docstrings or comments to code you did not change.
