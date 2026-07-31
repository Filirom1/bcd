#!/usr/bin/env python
import argparse
import subprocess
import sys


def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title:^58}")
    print("=" * 60)


def run_command(cmd, name):
    print(f"🚀 Running {name}...")
    print(f"   Command: {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {name} failed with exit code {e.returncode}")
        return False


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

    args = parser.parse_args()

    # If neither --js nor --python is specified, run both
    run_all = not args.js and not args.python
    run_js_suite = args.js or run_all
    run_py_suite = args.python or run_all

    success = True

    # 1. Run JavaScript Test Suite
    if run_js_suite:
        print_header("JavaScript Vitest Suite")
        js_cmd = ["npm", "run"]
        if args.coverage:
            js_cmd.append("test:js:coverage")
        else:
            js_cmd.append("test:js")

        js_ok = run_command(js_cmd, "JavaScript Vitest")
        if not js_ok:
            success = False

    # 2. Run Python Test Suite
    if run_py_suite:
        print_header("Python Pytest Suite")
        py_cmd = ["pytest", "tests"]

        if args.fast:
            py_cmd.extend(["-m", "not e2e and not slow"])

        # Inject or override coverage options
        if not args.coverage:
            # Strip coverage args from default addopts if coverage is disabled
            py_cmd.append("--no-cov")

        py_ok = run_command(py_cmd, "Python Pytest")
        if not py_ok:
            success = False

    # 3. Final Summary
    print_header("Test Suite Summary")
    if success:
        print("🟢 SUCCESS: All selected test suites passed!")
        sys.exit(0)
    else:
        print("🔴 FAILURE: One or more test suites failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
