import re
from pathlib import Path

import pytest

from src.shared import version


def test_version_matches_project_metadata():
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    assert match is not None
    expected_version = match.group(1)

    assert version.get_version() == expected_version
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
