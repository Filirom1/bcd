"""Tests for the release-time Godot export verifier."""

import pytest

from scripts.verify_godot_exports import check_project_configuration, output_has_magic


def test_godot_export_configuration_is_valid():
    """The checked-in project exposes both release presets and safety settings."""
    check_project_configuration()


def test_output_has_magic_accepts_matching_binary(tmp_path):
    """The verifier accepts a binary with the expected executable signature."""
    binary = tmp_path / "client.bin"
    binary.write_bytes(b"MZ" + b"payload")

    output_has_magic(binary, b"MZ")


def test_output_has_magic_rejects_wrong_signature(tmp_path):
    """The verifier rejects an artifact with the wrong executable signature."""
    binary = tmp_path / "client.bin"
    binary.write_bytes(b"not-an-executable")

    with pytest.raises(RuntimeError, match="Unexpected binary format"):
        output_has_magic(binary, b"\x7fELF")
