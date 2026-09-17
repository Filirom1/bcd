"""Call-number generation shared by catalog and inventory operations."""

import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Optional


def _normalize_ascii(value: str) -> str:
    """Return *value* without accents, like the web call-number generator."""
    return "".join(
        char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn"
    )


def _author_last_name(authors: Optional[Iterable[str]]) -> str:
    if not authors:
        return ""
    first = next(iter(authors), "") or ""
    if "," in first:
        return first.split(",", 1)[0].strip()
    return first.split()[-1].strip() if first.split() else ""


def _aut(authors: Optional[Iterable[str]]) -> str:
    return re.sub(r"[^A-Z]", "", _normalize_ascii(_author_last_name(authors)).upper())


def _strip_articles(value: Optional[str]) -> str:
    if not value:
        return ""
    result = value.strip()
    # Keep this in sync with the browser generator's supported articles.
    result = re.sub(r"^(les?|la|l'|une?|des?|d')\s+", "", result, count=1, flags=re.IGNORECASE)
    result = re.sub(r"^(the|an?)\s+", "", result, count=1, flags=re.IGNORECASE)
    result = re.sub(r"^l'", "", result, count=1, flags=re.IGNORECASE)
    result = re.sub(r"^d'", "", result, count=1, flags=re.IGNORECASE)
    return result


def _short_name(value: Optional[str], length: int, fallback: str) -> str:
    if not value or not value.strip():
        return fallback
    cleaned = re.sub(r"[^A-Z0-9]", "", _normalize_ascii(_strip_articles(value)).upper())
    return cleaned[:length] or fallback


def _full_name(value: Optional[str], fallback: str) -> str:
    if not value or not value.strip():
        return fallback
    cleaned = re.sub(r"[^A-Z0-9]+", " ", _normalize_ascii(_strip_articles(value)).upper()).strip()
    return re.sub(r"\s+", " ", cleaned) or fallback


def _matches(value: str, pattern: str) -> bool:
    """Match the simple leading/trailing wildcard syntax used by the UI."""
    value = value.lower()
    pattern = pattern.lower()
    if pattern.startswith("*") and pattern.endswith("*"):
        return pattern[1:-1] in value
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    if pattern.startswith("*"):
        return value.endswith(pattern[1:])
    return value == pattern


def parse_call_number_rules(value: Any) -> list[Mapping[str, Any]]:
    """Decode the JSON setting while tolerating an unset/malformed value."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    return [rule for rule in value or [] if isinstance(rule, Mapping)]


def generate_call_number(record: Any, rules: Any) -> str:
    """Generate one call number from a record and configured catalog rules.

    ``record`` may be an ORM object or a mapping.  The implementation mirrors the
    browser generator so a librarian gets the same result in cataloguing and in
    inventory bulk editing.
    """

    def get(name: str, default: Any = None) -> Any:
        if isinstance(record, Mapping):
            return record.get(name, default)
        return getattr(record, name, default)

    authors = get("authors") or []
    illustrators = get("illustrators") or []
    if isinstance(authors, str):
        try:
            authors = json.loads(authors)
        except (TypeError, ValueError):
            authors = []
    if isinstance(illustrators, str):
        try:
            illustrators = json.loads(illustrators)
        except (TypeError, ValueError):
            illustrators = []

    aut = _aut(authors)
    aut1, aut3 = aut[:1], aut[:3]
    ill = _aut(illustrators) or aut
    ill1, ill3 = ill[:1], ill[:3]
    collection = get("collection") or ""
    ser1 = _short_name(collection, 1, aut1)
    ser3 = _short_name(collection, 3, aut3)
    ser = _full_name(collection, aut3)
    title = _strip_articles(get("title") or "")
    title_clean = re.sub(r"[^A-Z0-9]", "", _normalize_ascii(title).upper())
    tit = _full_name(get("title") or "", "")
    tit1, tit3 = title_clean[:1], title_clean[:3]
    dewey = (get("dewey_number") or "").strip()
    medium = (get("medium_type") or "").strip()
    shelf = (get("shelf_location") or "").strip()

    selected = None
    for rule in parse_call_number_rules(rules):
        rule_medium = rule.get("medium_type")
        rule_shelf = rule.get("shelf_location")
        if rule_medium and not _matches(medium, str(rule_medium).strip()):
            continue
        if rule_shelf and not _matches(shelf, str(rule_shelf).strip()):
            continue
        selected = rule
        break

    if selected is None:
        return aut3
    pattern = str(selected.get("pattern") or "").strip()
    if not pattern:
        return ""
    values = {
        "AUT": aut,
        "AUT1": aut1,
        "AUT3": aut3,
        "SER": ser,
        "SER1": ser1,
        "SER3": ser3,
        "ILL": ill,
        "ILL1": ill1,
        "ILL3": ill3,
        "TIT": tit,
        "TIT1": tit1,
        "TIT3": tit3,
        "DEWEY": dewey,
    }
    for token, value in values.items():
        pattern = pattern.replace("{" + token + "}", value)
    return re.sub(r"\s+", " ", pattern).strip()
