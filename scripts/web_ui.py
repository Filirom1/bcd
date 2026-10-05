#!/usr/bin/env python3
"""Build, test, package, and manually exercise the BCD Web UI.

Examples:
    python scripts/web_ui.py --manual
    python scripts/web_ui.py --e2e
    python scripts/web_ui.py --portable --manual
    python scripts/web_ui.py --client-only
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run(command: list[str], env: dict[str, str]) -> None:
    """Run one command from the project root and stop on failure."""
    print(f"\n$ {' '.join(command)}")
    resolved_cmd = command.copy()
    binary_path = shutil.which(resolved_cmd[0])
    if binary_path:
        resolved_cmd[0] = binary_path
    subprocess.run(resolved_cmd, cwd=PROJECT_ROOT, env=env, check=True)


def portable_executable() -> Path:
    """Return the platform-specific PyInstaller executable path."""
    executable_name = "bcd.exe" if sys.platform == "win32" else "bcd"
    return PROJECT_ROOT / "dist" / "bcd" / executable_name


def configured_kids_client() -> bool:
    """Check whether the configured Kids client executable is available."""
    from src.bcd_api.core.config import settings
    from src.bcd_api.core.portable import get_app_dir

    configured_path = settings.kids_client_path.strip()
    if not configured_path:
        print("WARNING: KIDS_CLIENT_PATH is not configured.")
        return False

    executable = Path(configured_path)
    if not executable.is_absolute():
        executable = get_app_dir() / executable
    if not executable.is_file():
        print(f"WARNING: Kids client executable was not found: {executable}")
        return False
    return True


def run_mdns_proxy_only(port: int, env: dict[str, str]) -> None:
    """Run the minimal mDNS discovery API when the Kids executable is unavailable."""
    print(
        f"Starting the mDNS-only discovery service at http://127.0.0.1:{port}. "
        "Press Ctrl+C to stop."
    )
    try:
        run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.bcd_api.core.mdns_proxy:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            env,
        )
    except KeyboardInterrupt:
        print("\nStopped the mDNS discovery service.")


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
        "--client-only",
        action="store_true",
        help="launch the Kids client in client-only mode with its mDNS discovery proxy",
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

    if args.client_only:
        if args.portable:
            raise SystemExit("--client-only cannot be combined with --portable")
        if not configured_kids_client():
            run_mdns_proxy_only(args.port, env)
            return
        run(
            [
                sys.executable,
                "-m",
                "src.bcd_api.main",
                "--client-only",
                "--ui-mode",
                "kids",
                "--port",
                str(args.port),
            ],
            env,
        )
        return

    env["WEB_ASSETS_MODE"] = "build"
    env["ENVIRONMENT"] = "production"

    # Always produce a fresh, validated bundle before testing or packaging it.
    run(["npm", "run", "verify:web-build"], env)

    if args.e2e:
        run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/e2e/test_web_production.py",
                "-m",
                "e2e",
                "--cov-append",
                "-v",
            ],
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
