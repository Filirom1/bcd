#!/usr/bin/env python3
"""Build, test, package, and manually exercise the BCD Web UI.

Examples:
    python scripts/web_ui.py --manual
    python scripts/web_ui.py --e2e
    python scripts/web_ui.py --portable --manual
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str], env: dict[str, str]) -> None:
    """Run one command from the project root and stop on failure."""
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=True)


def portable_executable() -> Path:
    """Return the platform-specific PyInstaller executable path."""
    executable_name = "bcd.exe" if sys.platform == "win32" else "bcd"
    return PROJECT_ROOT / "dist" / "bcd" / executable_name


def parse_args() -> argparse.Namespace:
    """Parse Web UI workflow options."""
    parser = argparse.ArgumentParser(
        description="Build and exercise the BCD Web UI production bundle."
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="run the Playwright smoke test against FastAPI serving build/web",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="launch the built UI for manual testing (blocks until it is closed)",
    )
    parser.add_argument(
        "--portable",
        action="store_true",
        help="package the verified build with PyInstaller",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="host for manual mode (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="port for manual mode (default: 8888)",
    )
    return parser.parse_args()


def main() -> None:
    """Execute the selected Web UI workflow."""
    args = parse_args()
    env = os.environ.copy()
    env["WEB_ASSETS_MODE"] = "build"
    env["ENVIRONMENT"] = "production"

    # Always produce a fresh, validated bundle before testing or packaging it.
    run(["npm", "run", "verify:web-build"], env)

    if args.e2e:
        run(
            [sys.executable, "-m", "pytest", "tests/e2e/test_web_production.py", "--cov-append", "-v"],
            env,
        )

    if args.portable:
        run(["pyinstaller", "--clean", "bcd.spec"], env)

    if not args.manual:
        return

    if args.portable:
        executable = portable_executable()
        if not executable.is_file():
            raise RuntimeError(f"Portable executable was not created: {executable}")
        run([str(executable), "--host", args.host, "--port", str(args.port)], env)
    else:
        run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.bcd_api.main:app",
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--reload",
            ],
            env,
        )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
