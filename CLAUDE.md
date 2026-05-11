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

## Code quality

Run all four checks after **every** change and after **every** code review. Fix all reported issues before considering a change complete.

| Tool | Command | What it checks |
|---|---|---|
| ruff lint | `ruff check .` | Linting, import order, style rules |
| ruff format | `ruff format --check .` | Code formatting (run `ruff format .` to auto-fix) |
| mypy | `mypy custom_components/` | Static type checking |
| hassfest | CI only (`.github/workflows/validate.yml`) | HA manifest, strings, platform structure |

`hassfest` runs automatically on every push via GitHub Actions — it cannot be run locally without cloning the HA core repository.

- Do not add features, refactors, or "improvements" beyond what is explicitly requested.
- Do not add docstrings or comments to code you did not change.

## Home Assistant conventions

- **Python 3.9+** (mypy is configured for 3.9).
- Follow existing HA patterns: `CoordinatorEntity`, `async_setup_entry`, `async_unload_entry`.
- All async I/O goes through `EasyControls3Instance`; platform entities only read from the coordinator snapshot.
- Keep entity unique IDs tied to the device serial number so they survive IP changes.
- Do not add error handling for conditions that cannot occur given HA's `DataUpdateCoordinator` guarantees: when a platform entity accesses `coordinator.data`, `readCurrentData()` has always completed successfully, so all device properties are populated and never `None`.

## What to avoid

- Do not change the WebSocket binary frame format without also updating the parser in `EasyControls3Instance._parseData`.
- Do not introduce synchronous I/O inside async methods.

## Before committing

- Always ask if the version needs to be adjusted.
- Check for latest releases of required packages: run `pip index versions websockets` and `pip index versions python-dateutil`, then update the `>=` constraints in `manifest.json` if a newer stable version exists.
