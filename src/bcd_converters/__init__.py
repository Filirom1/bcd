"""BCD format converters.

Converters are grouped by their destination domain:

* :mod:`bcd_converters.catalog` contains catalog converters.
* :mod:`bcd_converters.borrower` contains borrower converters.

The ``list_converters`` and ``get_converter`` functions are kept as backwards-
compatible aliases for catalog converters.
"""

import ast
import importlib
import pkgutil
from pathlib import Path


def _list_converters(package_name: str, suffix: str) -> list[dict]:
    """Return metadata for converter modules in a converter subpackage."""
    package = importlib.import_module(package_name)
    converters = []
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if not module_name.endswith(suffix):
            continue
        name = module_name[: -len(suffix)]
        converters.append({
            "name": name,
            "description": _module_description(package, module_name),
        })
    return sorted(converters, key=lambda converter: converter["name"])


def _get_converter(package_name: str, name: str, suffix: str):
    """Import a converter from a domain-specific converter package."""
    return importlib.import_module(f"{package_name}.{name}{suffix}")


def _module_description(package, module_name: str) -> str:
    """Extract the first line of a converter module docstring."""
    module_file = Path(package.__file__).parent / f"{module_name}.py"
    if module_file.is_file():
        try:
            source = module_file.read_text(encoding="utf-8")
            doc = ast.get_docstring(ast.parse(source))
            if doc:
                return doc.splitlines()[0].strip()
        except Exception:
            pass

    try:
        module = importlib.import_module(f"{package.__name__}.{module_name}")
        doc = module.__doc__ or ""
        return doc.splitlines()[0].strip()
    except Exception:
        return ""


def list_catalog_converters() -> list[dict]:
    """Return metadata for catalog converters."""
    return _list_converters("bcd_converters.catalog", "_to_dublin_core")


def get_catalog_converter(name: str):
    """Import a catalog converter by its public format name."""
    return _get_converter("bcd_converters.catalog", name, "_to_dublin_core")


def list_borrower_converters() -> list[dict]:
    """Return metadata for borrower converters."""
    return _list_converters("bcd_converters.borrower", "_to_bcd_borrowers")


def get_borrower_converter(name: str):
    """Import a borrower converter by its public format name."""
    return _get_converter("bcd_converters.borrower", name, "_to_bcd_borrowers")


# Backwards compatibility: catalog was the original converter domain.
def list_converters() -> list[dict]:
    """Return metadata for catalog converters (legacy alias)."""
    return list_catalog_converters()


def get_converter(name: str):
    """Import a catalog converter (legacy alias)."""
    return get_catalog_converter(name)


def _get_description(module_name: str) -> str:
    """Compatibility helper for the old package-level private function."""
    if module_name.endswith("_to_dublin_core"):
        return _module_description(importlib.import_module("bcd_converters.catalog"), module_name)
    if module_name.endswith("_to_bcd_borrowers"):
        return _module_description(importlib.import_module("bcd_converters.borrower"), module_name)
    return ""
