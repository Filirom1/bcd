"""Tests for the global test ordering that protects asyncio from Playwright."""

from tests.conftest import pytest_collection_modifyitems


class FakeItem:
    """Minimal pytest item double used to test collection ordering."""

    def __init__(self, path, markers=()):
        self.fspath = path
        self.markers = set(markers)

    def add_marker(self, marker):
        self.markers.add(marker.name)

    def get_closest_marker(self, name):
        return name if name in self.markers else None


def test_collection_moves_all_e2e_tests_after_regular_tests():
    """Test async-capable regular tests run before Playwright session fixtures."""
    # ARRANGE
    browser_e2e = FakeItem("/project/tests/e2e/test_browser.py")
    regular = FakeItem("/project/tests/unit/test_async.py")
    cli_e2e = FakeItem("/project/tests/cli/test_e2e.py", markers=("e2e",))
    items = [browser_e2e, regular, cli_e2e]

    # ACT
    pytest_collection_modifyitems(config=None, items=items)

    # ASSERT
    assert items == [regular, browser_e2e, cli_e2e]
    assert "e2e" in browser_e2e.markers
