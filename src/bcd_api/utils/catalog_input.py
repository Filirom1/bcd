"""Pure helpers for classifying cataloging input values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_ISSN_RE = re.compile(r"^(?P<first>\d{4})-?(?P<last>\d{3}[\dXx])$")
_ISBN10_RE = re.compile(r"^[\d]{9}[\dXx]$")
_ISBN13_RE = re.compile(r"^(?:978|979)\d{10}$")
_EAN13_RE = re.compile(r"^\d{13}$")
_UNSUPPORTED_BARCODE_RE = re.compile(r"^[\d-]{8,20}$")
_PERIODICAL_ISSUE_SUFFIX_RE = re.compile(
    r"\s*(?:n[°o]?\s*\d+|num[eé]ro\s*\d+|vol\.\s*\d+|"
    r"fascicule\s*\d+|\d{4}/\d+).*$",
    re.IGNORECASE,
)
_EAN13_PERIODICAL_RE = re.compile(r"^977(\d{7})\d{3}$")


@dataclass(frozen=True)
class CatalogInput:
    """Classification of the value entered on the cataloging screen."""

    raw: str
    kind: str
    normalized_identifier: Optional[str] = None
    identifier_value: Optional[str] = None
    identifier_type: Optional[str] = None
    derived_from_ean: bool = False

    @property
    def is_identifier(self) -> bool:
        return self.identifier_type is not None

    @property
    def external_sources(self) -> list[str]:
        if self.identifier_type == "isbn":
            return ["bnf", "google_books"]
        if self.identifier_type == "issn":
            return ["sudoc"]
        return []


def _ean13_to_issn(ean13: str) -> Optional[str]:
    """Extract the ISSN encoded in a kiosk EAN-13 barcode (prefix 977)."""
    match = _EAN13_PERIODICAL_RE.match(ean13)
    if not match:
        return None
    digits = match.group(1)
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    check = (11 - (total % 11)) % 11
    check_char = "X" if check == 10 else str(check)
    return f"{digits[:4]}-{digits[4:7]}{check_char}"


def strip_periodical_issue_suffix(value: str) -> str:
    """Return a likely periodical title without a trailing issue designation."""
    return _PERIODICAL_ISSUE_SUFFIX_RE.sub("", (value or "").strip()).strip()


def _normalise_issn(value: str) -> Optional[str]:
    match = _ISSN_RE.fullmatch(value.replace(" ", ""))
    if not match:
        return None
    digits = f"{match.group('first')}{match.group('last')}".upper()
    return f"{digits[:4]}-{digits[4:]}"


def classify_catalog_input(value: str) -> CatalogInput:
    """Classify an ISBN, ISSN, periodical EAN, barcode, or free text.

    A barcode is deliberately not assumed to be an ISBN merely because it has
    13 digits.  Only ISBN-10/ISBN-13 shapes and EAN-977 periodical barcodes
    enter an external lookup route.
    """
    raw = (value or "").strip()
    if not raw:
        return CatalogInput(raw="", kind="text")

    explicit = raw.lower()
    if explicit.startswith("isbn:"):
        candidate = raw[5:].strip()
        compact = candidate.replace("-", "").replace(" ", "")
        if _ISBN10_RE.fullmatch(compact) or _ISBN13_RE.fullmatch(compact):
            return CatalogInput(
                raw=raw,
                kind="isbn",
                normalized_identifier=f"isbn:{compact.upper()}",
                identifier_value=compact.upper(),
                identifier_type="isbn",
            )
    elif explicit.startswith("issn:"):
        candidate = raw[5:].strip()
        issn = _normalise_issn(candidate)
        if issn:
            return CatalogInput(
                raw=raw,
                kind="issn",
                normalized_identifier=f"issn:{issn}",
                identifier_value=issn,
                identifier_type="issn",
            )

    compact = re.sub(r"[-\s]", "", raw)
    if _EAN13_RE.fullmatch(compact) and compact.startswith("977"):
        issn = _ean13_to_issn(compact)
        if issn:
            return CatalogInput(
                raw=raw,
                kind="ean977",
                normalized_identifier=f"issn:{issn}",
                identifier_value=issn,
                identifier_type="issn",
                derived_from_ean=True,
            )
        return CatalogInput(raw=raw, kind="unsupported_barcode")

    issn = _normalise_issn(raw)
    if issn:
        return CatalogInput(
            raw=raw,
            kind="issn",
            normalized_identifier=f"issn:{issn}",
            identifier_value=issn,
            identifier_type="issn",
        )

    if _ISBN10_RE.fullmatch(compact) or _ISBN13_RE.fullmatch(compact):
        return CatalogInput(
            raw=raw,
            kind="isbn",
            normalized_identifier=f"isbn:{compact.upper()}",
            identifier_value=compact.upper(),
            identifier_type="isbn",
        )

    if _UNSUPPORTED_BARCODE_RE.fullmatch(raw.replace(" ", "")):
        return CatalogInput(raw=raw, kind="unsupported_barcode")

    return CatalogInput(raw=raw, kind="text")


__all__ = [
    "CatalogInput",
    "classify_catalog_input",
    "strip_periodical_issue_suffix",
    "_ean13_to_issn",
]
