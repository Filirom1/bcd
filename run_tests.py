#!/usr/bin/env python
import argparse
import os
import subprocess
import sys
import time


def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title:^58}")
    print("=" * 60)


FAST_TEST_MARKER = "not e2e and not slow and not external"
SLOW_OR_EXTERNAL_TEST_MARKER = "not e2e and (slow or external)"
ACTIVE_E2E_TEST_MARKER = "e2e and not e2e_to_be_removed"
CI_TRUE_VALUES = {"1", "true", "yes"}


def should_show_logs(verbose):
    """Return whether suite output should stream to the terminal."""
    return verbose or os.environ.get("CI", "").lower() in CI_TRUE_VALUES


def run_command(cmd, name, verbose=False):
    """Run a suite, showing its output only when requested or on failure."""
    if verbose:
        print(f"🚀 Running {name}...")
        print(f"   Command: {' '.join(cmd)}")
    started_at = time.monotonic()
    options = {"check": False}
    if not verbose:
        options.update({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True})

    try:
        result = subprocess.run(cmd, **options)
    except OSError as exc:
        print(f"❌ {name} could not start: {exc}")
        return False

    duration = time.monotonic() - started_at
    if result.returncode == 0:
        print(f"✅ {name} passed in {duration:.1f}s")
        return True

    print(f"❌ {name} failed with exit code {result.returncode} after {duration:.1f}s")
    if not verbose and result.stdout:
        print("\n--- Captured test output ---")
        print(result.stdout.rstrip())
    print()
    return False


def pytest_command(*paths, marker=None, coverage=False, append_coverage=False):
    """Build an isolated pytest command for one test-suite boundary."""
    command = ["pytest", *paths]
    if marker:
        command.extend(["-m", marker])
    if coverage:
        if append_coverage:
            command.append("--cov-append")
    else:
        command.append("--no-cov")
    return command


def python_test_suites(fast, coverage):
    """Return Python suites split at event-loop and server ownership boundaries.

    Playwright's synchronous API keeps an event loop alive for the lifetime of
    its session fixtures. Running browser E2E tests in the same pytest process
    as pytest-asyncio tests makes their loop lifecycles overlap. The CLI E2E
    suite also owns a real uvicorn process. Each of those suites therefore gets
    its own pytest process.
    """
    suites = [
        (
            "Python Pytest (fast)",
            pytest_command("tests", marker=FAST_TEST_MARKER, coverage=coverage),
        )
    ]

    if fast:
        return suites

    suites.extend(
        [
            (
                "Python Pytest (slow/external)",
                pytest_command(
                    "tests",
                    marker=SLOW_OR_EXTERNAL_TEST_MARKER,
                    coverage=coverage,
                    append_coverage=coverage,
                ),
            ),
            (
                "CLI end-to-end Pytest",
                pytest_command(
                    "tests/cli/test_e2e_real_data.py",
                    coverage=coverage,
                    append_coverage=coverage,
                ),
            ),
            (
                "Browser end-to-end Pytest",
                pytest_command(
                    "tests/e2e",
                    marker=ACTIVE_E2E_TEST_MARKER,
                    coverage=coverage,
                    append_coverage=coverage,
                ),
            ),
        ]
    )
    return suites


def main():
    parser = argparse.ArgumentParser(
        description="BCD Unified Test Suite Runner (Python + JavaScript)"
    )
    parser.add_argument(
        "--js",
        action="store_true",
        help="Run JavaScript unit/component tests only",
    )
    parser.add_argument(
        "--python",
        action="store_true",
        help="Run Python backend/CLI tests only",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run fast tests only (skips slow, external, and E2E tests)",
    )
    parser.add_argument(
        "--cov",
        "--coverage",
        action="store_true",
        dest="coverage",
        help="Run with coverage collection enabled",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        "--show-logs",
        action="store_true",
        dest="verbose",
        help="Stream complete test-suite output (enabled automatically in CI)",
    )

    args = parser.parse_args()
    verbose = should_show_logs(args.verbose)

    # If neither --js nor --python is specified, run both
    run_all = not args.js and not args.python
    run_js_suite = args.js or run_all
    run_py_suite = args.python or run_all

    success = True

    # 1. Run JavaScript Test Suite
    if run_js_suite:
        if verbose:
            print_header("JavaScript Vitest Suite")
        js_cmd = ["npm", "run"]
        if args.coverage:
            js_cmd.append("test:js:coverage")
        else:
            js_cmd.append("test:js")

        js_ok = run_command(js_cmd, "JavaScript Vitest", verbose)
        if not js_ok:
            success = False

    # 2. Run Python Test Suite
    if run_py_suite:
        if verbose:
            print_header("Python Pytest Suite")
        for suite_name, py_cmd in python_test_suites(args.fast, args.coverage):
            if not run_command(py_cmd, suite_name, verbose):
                success = False

    # 3. Final Summary
    if verbose:
        print_header("Test Suite Summary")
    if success:
        print("🟢 SUCCESS: All selected test suites passed!")
        sys.exit(0)
    else:
        print("🔴 FAILURE: One or more test suites failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
