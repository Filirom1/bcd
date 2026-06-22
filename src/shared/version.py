"""Version management - single source of truth from pyproject.toml."""

import re
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_version() -> str:
    """
    Read version from pyproject.toml.

    This is the single source of truth for the application version.
    Uses LRU cache to avoid reading the file multiple times.

    Returns:
        Version string (e.g., "1.0.0")

    Raises:
        RuntimeError: If pyproject.toml is not found or version cannot be parsed
    """
    # PyInstaller frozen bundle: pyproject.toml is bundled into sys._MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        pyproject_path = Path(sys._MEIPASS) / "pyproject.toml"
        if not pyproject_path.exists():
            raise RuntimeError(
                f"Could not find pyproject.toml in bundle at {sys._MEIPASS}"
            )
    else:
        # Development: find pyproject.toml relative to this file
        # src/shared/version.py -> go up 2 levels to project root
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"

        if not pyproject_path.exists():
            # Fallback: try to find it by walking up the directory tree
            current = Path(__file__).parent
            for _ in range(5):  # Max 5 levels up
                if (current / "pyproject.toml").exists():
                    pyproject_path = current / "pyproject.toml"
                    break
                current = current.parent
            else:
                raise RuntimeError(
                    f"Could not find pyproject.toml. Searched from {Path(__file__).parent}"
                )

    try:
        content = pyproject_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to read {pyproject_path}: {e}")

    # Parse version using regex (works without tomllib dependency)
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if not match:
        raise RuntimeError(f"Could not find version field in {pyproject_path}")

    return match.group(1)


# Export version as module-level constant for convenience
__version__ = get_version()
