"""Tests for the isolated Python-suite orchestration in ``run_tests.py``."""

import subprocess
from unittest.mock import MagicMock

import run_tests


def test_should_show_logs_enables_verbose_mode_in_ci(monkeypatch):
    """Test CI runs stream logs without requiring a command-line flag."""
    # ARRANGE
    monkeypatch.setenv("CI", "true")

    # ACT / ASSERT
    assert run_tests.should_show_logs(verbose=False) is True


def test_should_show_logs_keeps_local_runs_concise_by_default(monkeypatch):
    """Test local runs remain concise unless verbose output is requested."""
    # ARRANGE
    monkeypatch.delenv("CI", raising=False)

    # ACT / ASSERT
    assert run_tests.should_show_logs(verbose=False) is False
    assert run_tests.should_show_logs(verbose=True) is True


def test_run_command_hides_successful_suite_output_by_default(monkeypatch, capsys):
    """Test concise mode captures successful test output instead of streaming it."""
    # ARRANGE
    mock_process = MagicMock()
    mock_process.stdout.read.side_effect = ["d", "o", "t", "s", ""]
    mock_process.poll.return_value = 0
    mock_process.wait.return_value = 0
    mock_popen = MagicMock(return_value=mock_process)
    monkeypatch.setattr(run_tests.subprocess, "Popen", mock_popen)

    # ACT
    succeeded = run_tests.run_command(["pytest"], "Pytest")

    # ASSERT
    assert succeeded is True
    mock_popen.assert_called_once()
    output = capsys.readouterr().out
    assert "detailed test output" not in output
    assert "Pytest passed" in output


def test_run_command_prints_captured_output_when_a_suite_fails(monkeypatch, capsys):
    """Test concise mode retains diagnostic output for a failing suite."""
    # ARRANGE
    mock_process = MagicMock()
    mock_process.stdout.read.side_effect = ["f", "a", "i", "l", "u", "r", "e", ""]
    mock_process.poll.return_value = 1
    mock_process.wait.return_value = 1
    mock_popen = MagicMock(return_value=mock_process)
    monkeypatch.setattr(run_tests.subprocess, "Popen", mock_popen)

    # ACT
    succeeded = run_tests.run_command(["pytest"], "Pytest")

    # ASSERT
    assert succeeded is False
    output = capsys.readouterr().out
    assert "failure" in output
    assert "Captured test output" in output


def test_run_command_streams_output_when_verbose(monkeypatch):
    """Test verbose mode leaves subprocess output attached to the terminal."""
    # ARRANGE
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(["pytest"], 0))
    monkeypatch.setattr(run_tests.subprocess, "run", mock_run)

    # ACT
    run_tests.run_command(["pytest"], "Pytest", verbose=True)

    # ASSERT
    mock_run.assert_called_once_with(["pytest"], check=False)


def test_python_test_suites_splits_loop_and_server_owners_without_coverage():
    """Test complete runs isolate browser and CLI E2E suites in subprocesses."""
    # ARRANGE / ACT
    suites = run_tests.python_test_suites(fast=False, coverage=False)

    # ASSERT
    assert [name for name, _ in suites] == [
        "Python Pytest (fast)",
        "Python Pytest (slow/external)",
        "CLI end-to-end Pytest",
        "Browser end-to-end Pytest",
    ]
    assert suites[0][1] == [
        "pytest",
        "tests",
        "-q",
        "-m",
        "not e2e and not slow and not external",
        "--no-cov",
    ]
    assert suites[1][1] == [
        "pytest",
        "tests",
        "-q",
        "-m",
        "not e2e and (slow or external)",
        "--no-cov",
    ]
    assert suites[2][1] == ["pytest", "tests/cli/test_e2e_real_data.py", "-q", "--no-cov"]
    assert suites[3][1] == [
        "pytest",
        "tests/e2e",
        "-q",
        "-m",
        "e2e and not e2e_to_be_removed",
        "--no-cov",
    ]


def test_python_test_suites_fast_runs_only_fast_non_external_tests():
    """Test fast mode excludes E2E, slow, and external test categories."""
    # ARRANGE / ACT
    suites = run_tests.python_test_suites(fast=True, coverage=False)

    # ASSERT
    assert suites == [
        (
            "Python Pytest (fast)",
            [
                "pytest",
                "tests",
                "-q",
                "-m",
                "not e2e and not slow and not external",
                "--no-cov",
            ],
        )
    ]


def test_python_test_suites_appends_coverage_across_isolated_processes():
    """Test coverage data from later subprocesses is combined with the first."""
    # ARRANGE / ACT
    suites = run_tests.python_test_suites(fast=False, coverage=True)

    # ASSERT
    assert "--no-cov" not in suites[0][1]
    assert "--cov-append" not in suites[0][1]
    assert all("--cov-append" in command for _, command in suites[1:])
