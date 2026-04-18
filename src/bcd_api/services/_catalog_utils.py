"""Shared text utilities for catalog enrichment services.

Used by google_books_service and sudoc_service for scoring
bibliographic matches. Extracted here to avoid duplication.
"""

import re
import unicodedata

STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "en",
    "au", "aux", "l", "d", "a", "sur", "dans", "j",
}


def normalize(s: str) -> str:
    """Lowercase, strip accents and punctuation — for scoring only."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def token_overlap(a: str, b: str) -> float:
    """Fraction of meaningful tokens in `a` that appear in `b`."""
    ta = set(normalize(a).split()) - STOPWORDS
    tb = set(normalize(b).split()) - STOPWORDS
    if not ta:
        return 0.5
    return len(ta & tb) / len(ta)


def score_match(orig_title: str, orig_lastname: str,
                found_title: str, found_authors: str) -> float:
    """Combined title + author similarity score (0.0 – 1.0).

    Perfect title match (≥1.0) → weight title more (85/15).
    Partial title match        → weight more balanced (65/35).
    """
    ts = token_overlap(orig_title, found_title)
    as_ = token_overlap(orig_lastname, found_authors) if orig_lastname else 0.5
    return (ts * 0.85 + as_ * 0.15) if ts >= 1.0 else (ts * 0.65 + as_ * 0.35)
