#!/usr/bin/env python3
"""Validate that manifest.json and const.py use the same DOMAIN."""

import json
import re
import sys
from pathlib import Path


def get_manifest_domain() -> str:
    """Extract domain from manifest.json."""
    manifest_path = Path(__file__).parent.parent / "custom_components" / "EasyControls3_homeassistant" / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest["domain"]


def get_const_domain() -> str:
    """Extract DOMAIN from const.py."""
    const_path = Path(__file__).parent.parent / "custom_components" / "EasyControls3_homeassistant" / "const.py"
    with open(const_path) as f:
        content = f.read()

    match = re.search(r'DOMAIN\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find DOMAIN in const.py")
    return match.group(1)


def main() -> int:
    """Validate domain consistency."""
    try:
        manifest_domain = get_manifest_domain()
        const_domain = get_const_domain()

        if manifest_domain != const_domain:
            print(f"❌ Domain mismatch!")
            print(f"   manifest.json: {manifest_domain}")
            print(f"   const.py:      {const_domain}")
            print()
            print("Fix: Update const.py to match manifest.json:")
            print(f"   DOMAIN = \"{manifest_domain}\"")
            return 1

        print(f"✅ Domains consistent: {manifest_domain}")
        return 0

    except Exception as e:
        print(f"❌ Error validating domains: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
