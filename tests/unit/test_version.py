from pathlib import Path

import pytest

from src.shared import version


def test_version_matches_project_metadata():
    assert version.get_version() == "1.1.0"
    assert version.__version__ == version.get_version()


def test_version_frozen_bundle_missing_pyproject(monkeypatch, tmp_path):
    version.get_version.cache_clear()
    monkeypatch.setattr(version.sys, "frozen", True, raising=False)
    monkeypatch.setattr(version.sys, "_MEIPASS", str(tmp_path), raising=False)
    with pytest.raises(RuntimeError, match="Could not find"):
        version.get_version()
    version.get_version.cache_clear()


def test_version_frozen_bundle_reads_metadata(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("version = '2.3.4'\n")
    version.get_version.cache_clear()
    monkeypatch.setattr(version.sys, "frozen", True, raising=False)
    monkeypatch.setattr(version.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert version.get_version() == "2.3.4"
    version.get_version.cache_clear()
