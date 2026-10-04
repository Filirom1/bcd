#!/usr/bin/env python3
"""Validate and optionally build/run the BCD Kids Godot exports."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "bcd_kids"
PRESETS = PROJECT / "export_presets.cfg"


def find_godot() -> str:
    configured = os.environ.get("GODOT_BIN")
    executable = configured if configured else shutil.which("godot") or shutil.which("godot4")
    if not executable:
        raise RuntimeError("Godot 4.6+ is required; set GODOT_BIN or add godot to PATH")
    return executable


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_project_configuration() -> None:
    project = read_text(PROJECT / "project.godot")
    presets = read_text(PRESETS)

    required_project_values = {
        "config/auto_accept_quit=false": "the quit confirmation guard",
        'renderer/rendering_method="gl_compatibility"': "the compatibility renderer",
        'run/main_scene="res://main.tscn"': "the main scene",
    }
    for value, description in required_project_values.items():
        if value not in project:
            raise RuntimeError(f"Missing {description}: {value}")

    for preset_name, platform, output_name in (
        ('name="Windows Desktop"', 'platform="Windows Desktop"', "BCD-Kids.exe"),
        ('name="Linux/X11"', 'platform="Linux"', "BCD-Kids.x86_64"),
    ):
        if preset_name not in presets or platform not in presets or output_name not in presets:
            raise RuntimeError(f"Incomplete export preset for {output_name}")

    if presets.count("binary_format/embed_pck=true") < 2:
        raise RuntimeError("Both export presets must embed the project PCK")
    if presets.count("debug/export_console_wrapper=0") < 2:
        raise RuntimeError("Both export presets must disable the console wrapper")

    for locale in ("en", "fr"):
        locale_path = PROJECT / "locales" / f"{locale}.json"
        if not locale_path.is_file():
            raise RuntimeError(f"Missing locale file: {locale_path}")
        import json

        data = json.loads(locale_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data:
            raise RuntimeError(f"Locale is not a non-empty JSON object: {locale_path}")

    print("Godot project and export preset configuration is valid")


def godot_version(godot: str) -> str:
    output = subprocess.check_output([godot, "--version"], text=True, stderr=subprocess.STDOUT)
    match = re.search(r"(\d+\.\d+\.\d+)", output)
    if not match:
        raise RuntimeError(f"Unable to determine Godot version from: {output.strip()}")
    return match.group(1)


def template_path(godot: str, filename: str) -> Path:
    version = godot_version(godot)
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / "Godot" / "export_templates" / f"{version}.stable" / filename
    return Path.home() / ".local" / "share" / "godot" / "export_templates" / f"{version}.stable" / filename


def run(command: list[str], *, env: dict[str, str], timeout: int | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=timeout)


def output_has_magic(path: Path, magic: bytes) -> None:
    if not path.is_file() or path.stat().st_size < len(magic):
        raise RuntimeError(f"Export was not created: {path}")
    with path.open("rb") as stream:
        if stream.read(len(magic)) != magic:
            raise RuntimeError(f"Unexpected binary format for {path}")


def run_export_smoke(executable: Path) -> None:
    env = os.environ.copy()
    env["BCD_GODOT_TESTS"] = "1"
    env["BCD_GODOT_EXPORT_SMOKE"] = "1"
    if os.name != "nt" and executable.suffix.lower() != ".exe":
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    run([str(executable), "--headless"], env=env, timeout=20)
    run(
        [str(executable), "--headless", "--script", "res://tests/export_readiness_test.gd"],
        env=env,
        timeout=30,
    )


def export_and_verify(godot: str, output_dir: Path) -> None:
    required_templates = {
        "Windows Desktop": ("windows_release_x86_64.exe", "MZ", b"MZ"),
        "Linux/X11": ("linux_release.x86_64", "ELF", b"\x7fELF"),
    }
    missing = [
        f"{name}: {template_path(godot, filename)}"
        for name, (filename, _label, _magic) in required_templates.items()
        if not template_path(godot, filename).is_file()
    ]
    if missing:
        raise RuntimeError(
            "Export templates are not installed. Missing:\n  " + "\n  ".join(missing)
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    run([godot, "--headless", "--import", "--path", str(PROJECT)], env=env, timeout=120)

    outputs = {
        "Windows Desktop": output_dir / "BCD-Kids.exe",
        "Linux/X11": output_dir / "BCD-Kids.x86_64",
    }
    for preset, output in outputs.items():
        run(
            [godot, "--headless", "--path", str(PROJECT), "--export-release", preset, str(output)],
            env=env,
            timeout=180,
        )

    output_has_magic(outputs["Windows Desktop"], b"MZ")
    output_has_magic(outputs["Linux/X11"], b"\x7fELF")
    print("Windows and Linux export binaries were created")

    # A Windows executable cannot run on Linux. CI on Windows can execute this
    # same verifier and will therefore cover both the export and its startup.
    if os.name == "nt":
        run_export_smoke(outputs["Windows Desktop"])
    elif sys.platform.startswith("linux"):
        run_export_smoke(outputs["Linux/X11"])
    else:
        print("Runtime smoke test skipped on this host")


def verify_existing(binary: Path, platform: str) -> None:
    expected_magic = b"MZ" if platform == "windows" else b"\x7fELF"
    output_has_magic(binary, expected_magic)
    print(f"{platform.capitalize()} export binary has the expected executable signature")

    host_platform = "windows" if os.name == "nt" else "linux" if sys.platform.startswith("linux") else "other"
    if host_platform == platform:
        run_export_smoke(binary)
    else:
        print(f"Runtime smoke test skipped: {platform} is not the CI host platform")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--actual",
        action="store_true",
        help="build both exports and run the host-native export smoke test",
    )
    mode.add_argument(
        "--verify-existing",
        type=Path,
        metavar="BINARY",
        help="verify an already-built platform binary without exporting again",
    )
    parser.add_argument(
        "--platform",
        choices=("windows", "linux"),
        help="platform of --verify-existing",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="directory for temporary export binaries (default: a temporary directory)",
    )
    args = parser.parse_args()

    check_project_configuration()
    if args.verify_existing is not None:
        if not args.platform:
            parser.error("--platform is required with --verify-existing")
        verify_existing(args.verify_existing, args.platform)
        return 0
    if not args.actual:
        return 0

    godot = find_godot()
    if args.output_dir is not None:
        export_and_verify(godot, args.output_dir)
        return 0
    with tempfile.TemporaryDirectory(prefix="bcd-godot-exports-") as directory:
        export_and_verify(godot, Path(directory))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Export verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
