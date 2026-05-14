# CLAUDE.md — HeliosEasyControls3_HA

## Project overview

This is a Home Assistant HACS custom integration for the **Helios easyControls 3.0** ventilation unit (KWL). Communication with the device uses WebSocket on port 80. The integration is written in Python and follows the Home Assistant component pattern.

Key files:
- [EasyControls3Instance.py](custom_components/HeliosEasyControls3_HA/EasyControls3Instance.py) — WebSocket client; parses raw binary frames from the device. Do not change the WebSocket binary frame format without also updating the parser in `EasyControls3Instance._parseData`.
- [__init__.py](custom_components/HeliosEasyControls3_HA/__init__.py) — HA entry point; sets up the `DataUpdateCoordinator` with a 60 s poll interval
- [config_flow.py](custom_components/HeliosEasyControls3_HA/config_flow.py) — UI config flow (only needs IP address)
- [const.py](custom_components/HeliosEasyControls3_HA/const.py) — shared constants (`DOMAIN`, etc.)
- [KWLStates.py](custom_components/HeliosEasyControls3_HA/KWLStates.py) — enum for KWL operating modes
- Platform modules: `sensor.py`, `number.py`, `select.py`, `switch.py`, `time.py`

## Ground rules

- Do not add features, refactors, or "improvements" beyond what is explicitly requested.
- Do not add docstrings or comments to code you did not change.

## General Code quality

Run all checks after every change. Fix all reported issues before considering a change complete.

| Tool | Command | What it checks |
|---|---|---|
| ruff lint | `ruff check .` | Linting, import order, style rules |
| ruff format | `ruff format --check .` | Code formatting (run `ruff format .` to auto-fix) |
| mypy | `mypy custom_components/` | Static type checking |
| pip-audit | see below | Known CVEs in dependencies |
| hassfest | CI only (`.github/workflows/validate.yml`) | HA manifest, strings, platform structure |

- **pip-audit** against `manifest.json` requirements (Windows):
```powershell
python -c "import json; reqs=json.load(open('custom_components/HeliosEasyControls3_HA/manifest.json'))['requirements']; open('_reqs_tmp.txt','w').write('\n'.join(reqs))" && pip-audit -r _reqs_tmp.txt && del _reqs_tmp.txt
```

- `hassfest` runs automatically on every push via GitHub Actions — it cannot be run locally without cloning the HA core repository.

## Home Assistant conventions

- **Python 3.12+** — always keep this in sync with the minimum Python version required by Home Assistant Core.
- Follow existing HA patterns: `CoordinatorEntity`, `async_setup_entry`, `async_unload_entry`.
- All async I/O goes through `EasyControls3Instance`; platform entities only read from the coordinator snapshot.
- Keep entity unique IDs tied to the device serial number so they survive IP changes. Do not include the domain or platform in the unique ID — HA composes the full key from those separately.
- Do not add error handling for conditions that cannot occur given HA's `DataUpdateCoordinator` guarantees: when a platform entity accesses `coordinator.data`, `readCurrentData()` has always completed successfully, so all device properties are populated and never `None`.
- Do not introduce synchronous I/O inside async methods.
- Call `coordinator.async_config_entry_first_refresh()` during setup; it raises `ConfigEntryNotReady` automatically on failure, which HA uses to retry setup.
- Never mutate a `ConfigEntry` directly — use `hass.config_entries.async_update_entry()`.
- Declare `PARALLEL_UPDATES` at the top of every platform module: `1` for write platforms (`number`, `select`, `switch`, `time`) to prevent concurrent device writes; `0` for read-only platforms (`sensor`, `binary_sensor`) to remove the default limit.
- Use `has_entity_name = True` on all entities and set `_attr_name` to only the entity-specific part (e.g. `"Outside Temperature"`). HA will prepend the device name automatically. Never build the full `"DeviceModel EntityName"` string manually.

## HACS publishing conventions (https://hacs.xyz/docs/publish/)

- `hacs.json` must exist in the repo root with `name` and `homeassistant` (minimum supported HA version).
- `manifest.json` must include: `domain`, `name`, `codeowners`, `documentation`, `issue_tracker`, `version`.
- Only one integration directory is allowed under `custom_components/`.
- Brand assets are required: `brands/icon.png` (512×512 PNG) in the repo root. Optionally also `brands/logo.png`.
- The GitHub repository must have a description and topics set — both are surfaced in the HACS UI.
- Use GitHub releases for versioning; the release tag is what HACS displays as the installed version.

## Before committing

- Always ask if the version needs to be adjusted.
- Check for latest releases of required packages: run `pip index versions websockets` and `pip index versions python-dateutil`, then update the `>=` constraints in `manifest.json` if a newer stable version exists.
