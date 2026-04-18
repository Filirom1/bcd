#!/usr/bin/env python3
"""Download vendor dependencies for offline use.

Usage:
    python scripts/download-vendor.py

To update a dependency:
    1. Edit vendor.json - change the version and url fields
    2. Re-run this script
"""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEPS_FILE = ROOT / "vendor.json"


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  {dest.name} ... ", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        size = dest.stat().st_size
        print(f"{size // 1024} KB")
    except Exception as e:
        print(f"FAILED: {e}")
        raise


def main() -> None:
    if not DEPS_FILE.exists():
        print(f"Error: {DEPS_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    with open(DEPS_FILE) as f:
        config = json.load(f)

    vendor_dir = ROOT / config["vendor_dir"]
    vendor_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for dep in config["dependencies"]:
        print(f"\n{dep['name']} v{dep['version']}")
        for file in dep["files"]:
            download_file(file["url"], vendor_dir / file["dest"])
            total += 1

    print(f"\nDone! {total} files downloaded to {vendor_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
