# Domain Management

## Overview

The integration domain is defined in `manifest.json` and **must** be kept in sync with `const.py`.

To avoid duplicate definitions, follow these rules:

### ✅ Single Source of Truth

- **Update ONLY `manifest.json`** when changing the domain
- A pre-commit hook automatically validates that `const.py` matches
- The hook runs on commit and will fail if inconsistent

### 📝 Example

If you need to change the domain:

1. Update `manifest.json`:
   ```json
   {
     "domain": "my_new_domain"
   }
   ```

2. Update `const.py`:
   ```python
   DOMAIN = "my_new_domain"
   ```

3. Commit - the pre-commit hook validates consistency automatically

### 🔧 Manual Validation

Run validation manually:
```bash
python scripts/validate_domain.py
```

Expected output on success:
```
✅ Domains consistent: HeliosEasyControls3_HA
```

### ⚠️ Pre-Commit Hook

The hook validates automatically before every commit:
- Defined in `.pre-commit-config.yaml` as `validate-domain-consistency`
- Runs only if `manifest.json` or `const.py` changes
- Fails with clear error message if domains don't match

### Why DRY Matters

While we have two files defining the domain:
- `manifest.json`: Home Assistant reads this for integration registration
- `const.py`: Python code imports and uses this constant

The pre-commit hook ensures they stay synchronized without a complex build process.
