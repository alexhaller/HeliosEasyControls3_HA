"""Regenerate docs/registers.json from a unit's web UI bundle.

The easyControls 3.0 web UI ships the firmware's full register table as
``VlxDevConstants.<NAME>=<address>`` assignments. That table is the
authoritative source for every address this integration uses.

Usage:
    python scripts/extract_registers.py <device-ip>
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import urllib.request
from pathlib import Path

ASSIGNMENT = re.compile(r"VlxDevConstants\.([A-Z][A-Z_0-9]+)\s*=\s*(\d+)")
DEST = Path(__file__).resolve().parent.parent / "docs" / "registers.json"


def fetch_bundle(host: str) -> str:
    with urllib.request.urlopen(f"http://{host}/js/bundle.js", timeout=30) as response:
        raw = response.read()
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass  # already plain text
    return raw.decode("utf-8", errors="replace")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    host = sys.argv[1]
    bundle = fetch_bundle(host)
    registers = {name: int(value) for name, value in ASSIGNMENT.findall(bundle)}
    if not registers:
        print("no VlxDevConstants assignments found - is this an easyControls 3 unit?")
        return 1

    payload = {
        "_source": "js/bundle.js of the easyControls 3.0 web UI (gzip-encoded), "
        "VlxDevConstants assignments",
        "_device": "Helios KWL 360 W ET",
        "_note": "Register address -> name. Read-buffer offset for the settings "
        "block is 182 + (address - 0x5000).",
        "registers": {
            str(address): name
            for name, address in sorted(registers.items(), key=lambda kv: kv[1])
        },
    }
    DEST.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{len(registers)} constants written to {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
