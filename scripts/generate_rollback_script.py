"""Generate the default rollback helper included in a portable release archive."""

import argparse
from pathlib import Path

from src.bcd_api.core.updater import (
    _write_rollback_script_linux,
    _write_rollback_script_windows,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("linux", "windows"))
    parser.add_argument("app_dir", type=Path)
    args = parser.parse_args()

    app_dir = args.app_dir
    app_dir.mkdir(parents=True, exist_ok=True)
    paths = (app_dir, Path("data"), Path("config"), Path("data/bcd.db"))
    if args.platform == "linux":
        _write_rollback_script_linux(*paths)
    else:
        _write_rollback_script_windows(*paths)


if __name__ == "__main__":
    main()
