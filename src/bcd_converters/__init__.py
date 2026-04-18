"""BCD format converters package.

Each module named *_to_dublin_core provides a catalog format converter with:
    convert(content: bytes) -> str

Modules can also be executed directly for debugging:
    python -m bcd_converters.bibliopuce_to_dublin_core input.csv output.csv
"""

import ast
import importlib
import pkgutil
from pathlib import Path


def list_converters() -> list[dict]:
    """Return metadata for all *_to_dublin_core converter modules in this package."""
    converters = []
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if not module_name.endswith('_to_dublin_core'):
            continue
        name = module_name[: -len('_to_dublin_core')]
        converters.append({'name': name, 'description': _get_description(module_name)})
    return sorted(converters, key=lambda c: c['name'])


def get_converter(name: str):
    """Import and return the converter module for *name*.

    Raises:
        ModuleNotFoundError: if no converter exists for the given format name.
    """
    return importlib.import_module(f'bcd_converters.{name}_to_dublin_core')


def _get_description(module_name: str) -> str:
    """Extract the first line of the module docstring.

    Tries AST parsing (fast, no side effects) in dev mode, where the .py
    file exists on disk.  Falls back to importing the module and reading
    __doc__ in frozen / packaged builds where only .pyc files are present.
    """
    module_file = Path(__file__).parent / f'{module_name}.py'
    if module_file.is_file():
        try:
            source = module_file.read_text(encoding='utf-8')
            doc = ast.get_docstring(ast.parse(source))
            if doc:
                return doc.splitlines()[0].strip()
        except Exception:
            pass

    # Frozen-app fallback: import the already-loaded module
    try:
        mod = importlib.import_module(f'bcd_converters.{module_name}')
        doc = mod.__doc__ or ''
        return doc.splitlines()[0].strip()
    except Exception:
        return ''
