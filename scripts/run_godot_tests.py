#!/usr/bin/env python3
"""Run the headless Godot test scripts and optional function coverage."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "bcd_kids"
TEST_ROOT = PROJECT / "tests"
COVERAGE_ROOTS = (PROJECT / "autoload", PROJECT / "src")
# Discovery is covered with synthetic DNS packets and offline screen tests, so
# it remains part of the normal production coverage denominator.
FUNCTION_DECLARATION = re.compile(
    r"^(?P<indent>[ \t]*)(?:(?:static)\s+)?func\s+(?P<name>[A-Za-z_]\w*)\s*\("
)


# ---------------------------------------------------------------------------
# Executable discovery and test selection
# ---------------------------------------------------------------------------


def find_godot() -> str | None:
    """Return the configured Godot executable, if one is available."""
    configured = os.environ.get("GODOT_BIN")
    if configured:
        return configured if Path(configured).is_file() else shutil.which(configured)
    return shutil.which("godot") or shutil.which("godot4")


def test_files(selected: list[str] | None) -> list[Path]:
    if selected:
        paths = []
        for value in selected:
            path = (ROOT / value).resolve()
            if not path.is_file() or TEST_ROOT not in path.parents or path.suffix != ".gd":
                raise SystemExit(f"Godot test must be a .gd file under {TEST_ROOT}: {value}")
            paths.append(path)
        return paths
    return sorted(TEST_ROOT.rglob("*_test.gd"))


# ---------------------------------------------------------------------------
# Function-level coverage
# ---------------------------------------------------------------------------


def relative_resource_path(path: Path, project_root: Path = PROJECT) -> str:
    return "res://" + path.relative_to(project_root).as_posix()


def leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def function_inventory(path: Path, project_root: Path = PROJECT) -> list[dict[str, Any]]:
    """Return named GDScript function declarations in *path*.

    This deliberately measures function coverage rather than pretending that
    stock Godot provides source-line coverage. Function entry instrumentation
    is stable for this project and works with the same Godot binary as normal
    tests, including Godot 4.6.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    functions: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = FUNCTION_DECLARATION.match(line)
        if not match:
            continue

        declaration_end = index
        while declaration_end < len(lines) and not lines[declaration_end].rstrip().endswith(":"):
            declaration_end += 1
        if declaration_end >= len(lines):
            continue

        body_index = declaration_end + 1
        while body_index < len(lines):
            stripped = lines[body_index].strip()
            if stripped and not stripped.startswith("#"):
                break
            body_index += 1

        functions.append(
            {
                "name": match.group("name"),
                "line": index + 1,
                "body_index": body_index,
                "body_indent": (
                    leading_whitespace(lines[body_index])
                    if body_index < len(lines)
                    else match.group("indent") + "\t"
                ),
                "path": relative_resource_path(path, project_root),
            }
        )
    return functions


def production_inventory(project_root: Path = PROJECT) -> dict[str, list[dict[str, Any]]]:
    inventory: dict[str, list[dict[str, Any]]] = {}
    for root in COVERAGE_ROOTS:
        copied_root = project_root / root.relative_to(PROJECT)
        for path in sorted(copied_root.rglob("*.gd")):
            resource_path = relative_resource_path(path, project_root)
            inventory[resource_path] = function_inventory(path, project_root)
    return inventory


def instrument_source(path: Path, project_root: Path) -> None:
    """Insert a probe at the beginning of every named function in a copy."""
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    functions = function_inventory(path, project_root)
    probes: dict[int, list[dict[str, Any]]] = {}
    for function in functions:
        body_index = int(function["body_index"])
        if body_index >= len(lines):
            continue
        probes.setdefault(body_index, []).append(function)

    instrumented: list[str] = []
    for index, line in enumerate(lines):
        for function in probes.get(index, []):
            path_literal = json.dumps(str(function["path"]))
            name_literal = json.dumps(str(function["name"]))
            indent = function["body_indent"]
            instrumented.extend(
                [
                    f"{indent}if Engine.get_main_loop() is SceneTree:\n",
                    f"{indent}\tvar __bcd_coverage_runtime = "
                    "(Engine.get_main_loop() as SceneTree).get_root().get_node_or_null("
                    f'"CoverageRuntime")\n',
                    f"{indent}\tif __bcd_coverage_runtime:\n",
                    f'{indent}\t\t__bcd_coverage_runtime.call("hit", '
                    f"{path_literal}, {name_literal}, {function['line']})\n",
                ]
            )
        instrumented.append(line)
    path.write_text("".join(instrumented), encoding="utf-8")


def make_coverage_project(destination: Path) -> tuple[Path, dict[str, list[dict[str, Any]]]]:
    """Create an isolated, instrumented copy of the Godot project."""
    shutil.copytree(
        PROJECT,
        destination,
        ignore=shutil.ignore_patterns(".godot", "builds", "venv", ".venv", "node_modules", "*.tmp"),
    )

    inventory = production_inventory(destination)
    for resource_path in inventory:
        path = destination / resource_path.removeprefix("res://")
        instrument_source(path, destination)

    project_file = destination / "project.godot"
    project_text = project_file.read_text(encoding="utf-8")
    autoload_header = "[autoload]\n"
    runtime_autoload = 'CoverageRuntime="*res://tests/coverage_runtime.gd"\n'
    if autoload_header not in project_text:
        raise RuntimeError("Unable to add coverage autoload: project has no [autoload] section")
    project_file.write_text(
        project_text.replace(autoload_header, autoload_header + runtime_autoload, 1),
        encoding="utf-8",
    )
    return destination, inventory


def merge_coverage(
    inventory: dict[str, list[dict[str, Any]]], reports: list[Path]
) -> dict[str, Any]:
    hits: dict[str, dict[str, dict[str, Any]]] = {}
    for report_path in reports:
        if not report_path.is_file():
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for script_path, functions in report.get("hits", {}).items():
            destination = hits.setdefault(script_path, {})
            for function_name, details in functions.items():
                current = destination.setdefault(
                    function_name,
                    {"line": int(details.get("line", 0)), "hits": 0},
                )
                current["line"] = int(details.get("line", current.get("line", 0)))
                current["hits"] = int(current.get("hits", 0)) + int(details.get("hits", 0))

    files: list[dict[str, Any]] = []
    total_functions = 0
    covered_functions = 0
    for script_path, functions in inventory.items():
        script_hits = hits.get(script_path, {})
        entries = []
        for function in functions:
            name = str(function["name"])
            hit_count = int(script_hits.get(name, {}).get("hits", 0))
            covered = hit_count > 0
            total_functions += 1
            covered_functions += int(covered)
            entries.append(
                {
                    "name": name,
                    "line": int(function["line"]),
                    "hits": hit_count,
                    "covered": covered,
                }
            )
        files.append(
            {
                "path": script_path,
                "functions": entries,
                "total": len(entries),
                "covered": sum(1 for entry in entries if entry["covered"]),
                "coverage_percent": (
                    round(100.0 * sum(1 for entry in entries if entry["covered"]) / len(entries), 1)
                    if entries
                    else 100.0
                ),
            }
        )

    return {
        "format": "bcd-godot-function-coverage-v1",
        "metric": "function-entry",
        "total_functions": total_functions,
        "covered_functions": covered_functions,
        "coverage_percent": (
            round(100.0 * covered_functions / total_functions, 1) if total_functions else 100.0
        ),
        "files": files,
    }


def write_coverage_reports(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    text_path = output_path.with_suffix(".txt")
    lines = [
        "BCD Godot function coverage",
        "============================",
        "Metric: function entry coverage (not source-line coverage)",
        "Total: %d/%d functions (%.1f%%)"
        % (
            report["covered_functions"],
            report["total_functions"],
            report["coverage_percent"],
        ),
        "",
    ]
    for file_report in report["files"]:
        lines.append(
            "%6.1f%% %3d/%-3d %s"
            % (
                file_report["coverage_percent"],
                file_report["covered"],
                file_report["total"],
                file_report["path"],
            )
        )
        for function in file_report["functions"]:
            if not function["covered"]:
                lines.append("         missing %s:%d" % (function["name"], function["line"]))
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    lcov_path = output_path.with_suffix(".lcov")
    lcov: list[str] = []
    for file_report in report["files"]:
        lcov.extend(["TN:", "SF:" + file_report["path"]])
        for function in file_report["functions"]:
            lcov.append("FN:%d,%s" % (function["line"], function["name"]))
        for function in file_report["functions"]:
            lcov.append("FNDA:%d,%s" % (function["hits"], function["name"]))
        lcov.extend(
            [
                "FNF:%d" % file_report["total"],
                "FNH:%d" % file_report["covered"],
                "LF:%d" % file_report["total"],
                "LH:%d" % file_report["covered"],
                "end_of_record",
            ]
        )
    lcov_path.write_text("\n".join(lcov) + "\n", encoding="utf-8")

    html_path = output_path.with_suffix(".html")
    rows = "\n".join(
        "<tr><td>{path}</td><td>{covered}/{total}</td><td>{coverage_percent:.1f}%</td></tr>".format(
            **file_report
        )
        for file_report in report["files"]
    )
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>BCD Godot function coverage</title>"
        "<style>body{font:14px sans-serif;margin:2rem}table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:.35rem .6rem;text-align:left}</style>"
        "<h1>BCD Godot function coverage</h1>"
        "<p>%d/%d functions covered (%.1f%%)</p>"
        "<table><tr><th>Script</th><th>Covered</th><th>Coverage</th></tr>%s</table>"
        % (
            report["covered_functions"],
            report["total_functions"],
            report["coverage_percent"],
            rows,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Test execution
# ---------------------------------------------------------------------------


def prepare_project(executable: str, project: Path, env: dict[str, str]) -> int:
    """Import the project so class_name scripts are available in clean CI copies."""
    command = [executable, "--headless", "--editor", "--path", str(project), "--quit"]
    print("$", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    return result.returncode


def run_test(
    executable: str,
    path: Path,
    project: Path,
    env: dict[str, str],
) -> int:
    relative_test = path.relative_to(PROJECT).as_posix()
    command = [
        executable,
        "--headless",
        "--path",
        str(project),
        "--script",
        f"res://{relative_test}",
    ]
    print("$", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test",
        action="append",
        dest="tests",
        help="Run one test file (repository-relative); may be repeated",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Collect function-entry coverage in an isolated project copy",
    )
    parser.add_argument(
        "--coverage-file",
        default="coverage-godot/coverage.json",
        help="JSON output path for coverage (default: coverage-godot/coverage.json)",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=None,
        help="Fail when function coverage is below this percentage",
    )
    args = parser.parse_args()
    if args.coverage_threshold is not None:
        args.coverage = True

    executable = find_godot()
    if executable is None:
        print("Skipping Godot tests: godot is not installed", flush=True)
        return 0

    paths = test_files(args.tests)
    if not paths:
        print(f"No Godot tests found under {TEST_ROOT}", flush=True)
        return 0

    with tempfile.TemporaryDirectory(prefix="bcd-godot-tests-") as temporary:
        temporary_root = Path(temporary)
        project = PROJECT
        inventory: dict[str, list[dict[str, Any]]] = {}
        if args.coverage:
            project, inventory = make_coverage_project(temporary_root / "project")

        godot_env = os.environ.copy()
        godot_env["BCD_GODOT_TESTS"] = "1"
        for variable, directory_name in (
            ("HOME", "home"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_CACHE_HOME", "cache"),
        ):
            directory = temporary_root / directory_name
            directory.mkdir()
            godot_env[variable] = str(directory)

        prepare_returncode = prepare_project(executable, project, godot_env)
        if prepare_returncode != 0:
            print("Godot project import failed", flush=True)
            return prepare_returncode

        coverage_reports: list[Path] = []
        for index, path in enumerate(paths):
            if args.coverage:
                coverage_path = temporary_root / f"coverage-{index}.json"
                godot_env["GODOT_COVERAGE_FILE"] = str(coverage_path)
            else:
                godot_env.pop("GODOT_COVERAGE_FILE", None)
                coverage_path = None

            returncode = run_test(executable, path, project, godot_env)
            if coverage_path is not None:
                coverage_reports.append(coverage_path)
            if returncode != 0:
                print(f"Godot test failed: {path.relative_to(ROOT)}", flush=True)
                return returncode

        if args.coverage:
            report = merge_coverage(inventory, coverage_reports)
            output_path = (ROOT / args.coverage_file).resolve()
            write_coverage_reports(report, output_path)
            print(
                "Godot function coverage: %d/%d (%.1f%%)"
                % (
                    report["covered_functions"],
                    report["total_functions"],
                    report["coverage_percent"],
                ),
                flush=True,
            )
            if (
                args.coverage_threshold is not None
                and report["coverage_percent"] < args.coverage_threshold
            ):
                print(
                    "Godot function coverage below threshold: %.1f%% < %.1f%%"
                    % (report["coverage_percent"], args.coverage_threshold),
                    flush=True,
                )
                return 1

    print(f"Godot tests passed ({len(paths)} script(s))", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
