#!/usr/bin/env python3
"""Enrich a BiblioPuce CSV export via BNF + Google Books + SUDOC.

Lookup priority:
  1. BNF (catalogue.bnf.fr)  — best coverage for French editions
  2. Google Books             — fallback for books, good for recent ISBNs
  3. SUDOC (sudoc.abes.fr)   — French university catalogue, strong on:
       • youth periodicals (Wapiti, J'aime lire, Arkéo junior…)
       • classics without ISBN
       • ISBNs not found by BNF/Google

All raw API responses are cached on disk (bnf_cache/, google_cache/,
sudoc_cache/) — the script can be interrupted and resumed without
repeating already-completed requests.

Outputs:
  • output.csv           — full file: all original columns + all enriched columns
  • output_bibliopuce.csv — BiblioPuce-format file with enriched values applied

──────────────────────────────────────────────────────────────────────────────
FIELD MAPPING — what the script does to each column
──────────────────────────────────────────────────────────────────────────────

BIBLIOGRAPHIC RECORD fields
───────────────────────────
  Titre         Replaced by enriched_title (BNF > Google > SUDOC > original)
  SousTitre     Filled if empty  ← bnf_subtitle / google_subtitle
  Auteur        Replaced by enriched_authors (BNF > Google > SUDOC > original)
  Illustrateur  Unchanged
  ISBN          Replaced by isbn_found (normalised: no dashes, no prefix)
  Annee         Replaced by enriched_year (BNF > Google > SUDOC > original)
  Editeur       Replaced by enriched_publisher (BNF > Google > SUDOC > original)
  Collection    Filled if empty  ← bnf_series
  Numero        Filled if empty  ← bnf_series_vol
  Support       Corrected/filled using multiple signals (priority order):
                  1. Genre field forces override when unambiguous:
                       "Revues et magazines" → Périodique
                       "Contes" (wrongly set to Périodique) → Conte
                       "Poèmes et comptines" (wrongly set to Périodique) → Poème
                       "Bandes dessinées" → Bande dessinée
                       "Album/Albums" → Album illustré
                       "Romans et nouvelles" → Livre
                  2. enriched_medium_type from BNF tag 608/181 and Google
                     categories (when no genre override)
                Valid BCD values: Livre, Album illustré, Conte, Poème,
                  Périodique, Bande dessinée, Manga, DVD, CD, Autre
  Genre         Unchanged
  Rubrique      Unchanged
  Niveau        Normalised to BCD catalog_levels vocabulary:
                  "Cours préparatoire" → CP
                  "Cours élémentaire"  → CE1  (approximation)
                  "Cours moyen"        → CM1  (approximation)
                  "Secondaire"         → 6e   (approximation)
                  Cycles left unchanged (too ambiguous to map to a single year)
  Mots-clefs    Filled if empty  ← bnf_subjects (RAMEAU subject headings)
  Description   Filled if empty  ← bnf_description / google_description
  Taille        Filled if empty  ← bnf_pages

ITEM (exemplaire) fields
────────────────────────
  Inventaire    Unchanged (becomes the item barcode in BCD)
  Cote          Filled if empty ← enriched_cote (see below)
                  Documentaires (Dewey 0–7xx, 9xx): "591.5 WHI"
                  Fiction (Dewey 8xx or genre-based):
                    Romans        → "R AUT"
                    Bande dessinée → "BD AUT"
                    Album illustré → "A AUT"
                    Conte         → "C AUT"
                    Poème         → "P AUT"
  Date achat    Unchanged
  Financement   Unchanged
  Empruntable   Unchanged

EXTRA columns added to output_bibliopuce.csv (not in original BiblioPuce format)
──────────────────────────────────────────────────────────────────────────────
  enriched_medium_type  Inferred medium type before Support override
  enriched_cote         Computed call number (review before importing)

EXTRA columns available only in output.csv
──────────────────────────────────────────
  bnf_*         Raw BNF fields (title, authors, year, series, pages,
                  subjects, description, genre, dewey, language, …)
  google_*      Raw Google Books fields (title, authors, year, pages,
                  categories, language, thumbnail, description)
  sudoc_*       Raw SUDOC fields (title, authors, year, isbn, issn, …)
  isbn_source   Match source: bnf_isbn | bnf_title | google_isbn |
                  google_title | sudoc_isbn | sudoc_issn | sudoc_title
  isbn_confidence  high (ISBN match or score ≥ 0.75) | low
  cover_image   Cover filename if --covers-dir is set

──────────────────────────────────────────────────────────────────────────────
Usage:
    python scripts/enrich_bibliopuce.py input.csv output.csv
    python scripts/enrich_bibliopuce.py input.csv output.csv --api-key AIza...
    python scripts/enrich_bibliopuce.py input.csv output.csv --limit 20
    python scripts/enrich_bibliopuce.py input.csv output.csv --min-score 0.65
    python scripts/enrich_bibliopuce.py input.csv output.csv --covers-dir data/covers
"""

import argparse
import csv
import io
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BNF_URL    = "http://catalogue.bnf.fr/api/SRU"
GOOGLE_URL = "https://www.googleapis.com/books/v1/volumes"
SUDOC_URL  = "https://www.sudoc.abes.fr/cbs/sru/"
COVERS_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"

RATE_INTERVAL = 1.1  # seconds between requests (slightly over 1 s to be safe)
STOPWORDS = {"le","la","les","un","une","des","de","du","et","en","au","aux",
             "l","d","a","sur","dans","j"}

# ISSN : format XXXX-XXXC (4 chiffres, tiret, 3 chiffres + chiffre ou X)
ISSN_PATTERN   = re.compile(r"^\d{4}-\d{3}[\dX]$")
# Supprime le numéro de fascicule en fin de titre ("n° 205", "num. 12", "#3"…)
ISSUE_STRIP_RE = re.compile(
    r"\s*(n[°o°]?\s*\d+\b|num[ée]ro\s*\d+\b|#\s*\d+\b).*$", re.IGNORECASE
)

ENRICHED_COLUMNS = [
    "isbn_found", "isbn_source", "isbn_confidence",
    "bnf_title", "bnf_subtitle", "bnf_authors", "bnf_publisher", "bnf_year",
    "bnf_series", "bnf_series_vol", "bnf_pages", "bnf_dimensions",
    "bnf_language", "bnf_subjects", "bnf_description", "bnf_genre",
    "google_title", "google_subtitle", "google_authors", "google_publisher",
    "google_year", "google_pages", "google_categories", "google_language",
    "google_thumbnail", "google_description",
    "sudoc_title", "sudoc_authors", "sudoc_publisher", "sudoc_year",
    "sudoc_isbn", "sudoc_issn", "sudoc_language", "sudoc_series",
    "enriched_title", "enriched_authors", "enriched_publisher", "enriched_year",
    "enriched_medium_type", "enriched_cote",
    "bnf_dewey",
    "bnf_strategy", "google_strategy", "sudoc_strategy",
    "match_score", "source_count", "needs_review",
    "cover_image",
]

# Mapping Genre BiblioPuce → medium_type BCD
# Overrides le Support existant si incohérent (ex: Genre=Contes + Support=Périodique)
_GENRE_TO_MEDIUM: dict[str, str] = {
    "bandes dessinées":    "Bande dessinée",
    "album":               "Album illustré",
    "albums":              "Album illustré",
    "revues et magazines": "Périodique",
    "contes":              "Conte",
    "poèmes et comptines": "Poème",
    "romans et nouvelles": "Livre",
}

# Normalisation Niveau BiblioPuce → catalog_levels BCD
_NIVEAU_MAP: dict[str, str] = {
    "cours préparatoire":  "CP",
    "cp":                  "CP",
    "cours élémentaire 1": "CE1",
    "ce1":                 "CE1",
    "cours élémentaire 2": "CE2",
    "ce2":                 "CE2",
    "cours élémentaire":   "CE1",   # approximation
    "cours moyen 1":       "CM1",
    "cm1":                 "CM1",
    "cours moyen 2":       "CM2",
    "cm2":                 "CM2",
    "cours moyen":         "CM1",   # approximation
    "sixième":             "6e",
    "secondaire":          "6e",    # approximation
    "tous niveaux":        "Tous niveaux",
}

# Normalisation codes langue BNF (ISO 639-2) → BCD (ISO 639-1)
_LANG_MAP: dict[str, str] = {
    "fre": "fr", "fra": "fr",
    "eng": "en",
    "spa": "es",
    "ger": "de", "deu": "de",
    "ara": "ar",
    "ita": "it",
    "por": "pt",
    "nld": "nl", "dut": "nl",
}

# Mapping BNF tag 608 (genre CNLJ) → medium_type BCD
_BNF_608_MEDIUM: dict[str, str] = {
    "bandes dessinées":            "Bande dessinée",
    "albums":                      "Album illustré",
    "romans":                      "Livre",
    "premières lectures":          "Livre",
    "ouvrages pour la jeunesse":   "Livre",
    "contes, légendes et folklore":"Livre",
}
_BNF_608_MEDIUM_PREFIX: list[tuple[str, str]] = [
    ("documentaires", "Livre"),
]

# Mapping BNF tag 181/c (RDA content type) → medium_type BCD
_RDA_CONTENT_MEDIUM: dict[str, str] = {
    "prm": "CD",   # performed music
    "tdi": "DVD",  # two-dimensional moving image (video)
    "tdf": "DVD",  # three-dimensional form (rare, treat as video)
}

# Google categories → medium_type BCD
_GOOGLE_BD_CATEGORIES = {
    "comics & graphic novels", "bandes dessinées",
    "comic books, strips, etc", "caricatures and cartoons",
}
_GOOGLE_MANGA_CATEGORIES = {"manga"}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_last_request = 0.0

def _wait():
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < RATE_INTERVAL:
        time.sleep(RATE_INTERVAL - elapsed)
    _last_request = time.time()


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_query(s: str) -> str:
    """Lowercase, remove quote chars that break SRU/Google syntax."""
    s = s.lower()
    s = re.sub(r'["\']', " ", s)
    return re.sub(r"\s+", " ", s).strip()


def token_overlap(a: str, b: str) -> float:
    ta = set(normalize(a).split()) - STOPWORDS
    tb = set(normalize(b).split()) - STOPWORDS
    if not ta:
        return 0.5
    return len(ta & tb) / len(ta)


def score_match(orig_title: str, orig_lastname: str,
                found_title: str, found_authors: str) -> float:
    ts = token_overlap(orig_title, found_title)
    as_ = token_overlap(orig_lastname, found_authors) if orig_lastname else 0.5
    return (ts * 0.85 + as_ * 0.15) if ts >= 1.0 else (ts * 0.65 + as_ * 0.35)


def is_empty(val: str) -> bool:
    return val.strip().strip('"') == ""


def clean_isbn(isbn: str) -> str:
    return isbn.strip().strip('"').replace("-", "").replace(".", "").replace(" ", "")


def _prefer_isbn13(isbns: list[str]) -> str:
    """From a list of ISBNs, return ISBN-13 if available, else first found."""
    cleaned = [clean_isbn(i) for i in isbns if i]
    for i in cleaned:
        if len(i) == 13:
            return i
    return cleaned[0] if cleaned else ""


def parse_author_lastname(raw: str) -> str:
    """'Aymé (Marcel)' → 'Aymé'"""
    m = re.match(r"^(.+?)\s*\((.+?)\)$", raw.strip())
    return m.group(1).strip() if m else raw.strip()


def cache_key(row: dict) -> str:
    isbn = clean_isbn(row.get("ISBN", ""))
    if isbn:
        return isbn
    return f"title_{row.get('Inventaire', 'unknown').strip()}"


# ---------------------------------------------------------------------------
# BNF API
# ---------------------------------------------------------------------------

def bnf_request(query: str, max_records: int = 5) -> str | None:
    params = urllib.parse.urlencode({
        "version": "1.2",
        "operation": "searchRetrieve",
        "query": query,
        "maximumRecords": str(max_records),
    })
    _wait()
    try:
        with urllib.request.urlopen(f"{BNF_URL}?{params}", timeout=10) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  [BNF error] {e}", file=sys.stderr)
        return None


def bnf_parse_nb(xml_text: str) -> int:
    try:
        root = ET.fromstring(xml_text)
        for el in root.iter():
            if el.tag.endswith("numberOfRecords"):
                return int(el.text)
    except Exception:
        pass
    return 0


def bnf_extract_results(xml_text: str) -> list[dict]:
    results = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return results

    def get_vals(rec, tag, code):
        return [sf.text.strip() for df in rec.iter()
                if df.get("tag") == tag
                for sf in df if sf.get("code") == code and sf.text]

    for rec in root.iter():
        if rec.tag.endswith("record") and rec.get("tag") is None:
            isbns   = get_vals(rec, "010", "a")
            titles  = get_vals(rec, "200", "a")
            subs    = get_vals(rec, "200", "e")
            lnames  = get_vals(rec, "700", "a")
            fnames  = get_vals(rec, "700", "b")
            authors = [f"{f} {l}".strip() for f, l in zip(fnames, lnames)] or lnames
            pubs    = get_vals(rec, "210", "c")
            dates   = get_vals(rec, "210", "d")
            series  = get_vals(rec, "225", "a")
            ser_vol = get_vals(rec, "225", "v")
            pages   = get_vals(rec, "215", "a")
            dims    = get_vals(rec, "215", "d")
            langs   = get_vals(rec, "101", "a")
            subjs   = get_vals(rec, "606", "a")
            descs   = get_vals(rec, "330", "a")
            genres  = get_vals(rec, "608", "a")
            rda_content = get_vals(rec, "181", "c")  # RDA content type (txt/sti/prm/tdi…)
            deweys  = get_vals(rec, "676", "a")       # Dewey Decimal Classification
            results.append({
                "isbns": isbns, "titles": titles, "subtitles": subs,
                "authors": authors, "publishers": pubs, "dates": dates,
                "series": series, "series_vol": ser_vol,
                "pages": pages, "dims": dims,
                "languages": langs, "subjects": subjs, "descriptions": descs,
                "genres": genres, "rda_content": rda_content, "deweys": deweys,
            })
    return results


def infer_medium_type(bnf_result: dict | None, google_result: dict | None,
                      sudoc_result: dict | None, is_issn: bool) -> str:
    """Déduit le medium_type BCD depuis BNF (608/181), Google (categories) et SUDOC (issn).

    Priorité : ISSN > BNF 181 (CD/DVD) > BNF 608 > Google categories.
    Retourne '' si aucun signal fiable.
    """
    # ISSN détecté → toujours Périodique
    if is_issn or (sudoc_result and sudoc_result.get("issn")):
        return "Périodique"

    # BNF tag 181/c → CD / DVD (plus fort que le genre textuel)
    if bnf_result:
        for rda in bnf_result.get("rda_content", []):
            medium = _RDA_CONTENT_MEDIUM.get(rda.strip())
            if medium:
                return medium

        # BNF tag 608 → genre CNLJ
        for genre in bnf_result.get("genres", []):
            g = genre.strip().lower()
            medium = _BNF_608_MEDIUM.get(g)
            if medium:
                return medium
            for prefix, m in _BNF_608_MEDIUM_PREFIX:
                if g.startswith(prefix):
                    return m

    # Google categories → BD / Manga
    if google_result:
        for cat in google_result.get("categories", []):
            c = cat.strip().lower()
            if c in _GOOGLE_MANGA_CATEGORIES:
                return "Manga"
            if c in _GOOGLE_BD_CATEGORIES:
                return "Bande dessinée"

    return ""


def bnf_best(orig_title: str, orig_lastname: str, results: list[dict],
             min_score: float = 0.45) -> dict | None:
    if not results:
        return None
    scored = sorted(
        results,
        key=lambda r: score_match(
            orig_title, orig_lastname,
            r["titles"][0] if r["titles"] else "",
            " ".join(r["authors"])
        ),
        reverse=True
    )
    best = scored[0]
    sc = score_match(
        orig_title, orig_lastname,
        best["titles"][0] if best["titles"] else "",
        " ".join(best["authors"])
    )
    if sc < min_score:
        return None
    best["_score"] = round(sc, 3)
    best["_confidence"] = "high" if sc >= 0.75 else "low"
    return best


def bnf_lookup_isbn(isbn: str) -> str | None:
    """Single BNF lookup by ISBN. Returns raw XML."""
    return bnf_request(f'bib.isbn adj "{isbn}"', max_records=1)


def bnf_search_title(title: str, lastname: str) -> tuple[str | None, str]:
    """Try up to 4 strategies. Returns (raw_xml, strategy_name)."""
    qt = clean_query(title)
    ql = clean_query(lastname)
    nt = normalize(title)
    keywords = [w for w in nt.split() if w not in STOPWORDS]

    strategies = [
        (f'(bib.title all "{qt}") and (bib.author all "{ql}")', "title+author"),
        (f'(bib.title all "{nt}") and (bib.author all "{ql}")', "norm+author"),
        (f'bib.title all "{qt}"', "title-only"),
    ]
    if len(keywords) >= 3:
        strategies.append(
            (f'bib.title all "{" ".join(keywords[:4])}"', "keywords")
        )

    for query, strategy in strategies:
        xml = bnf_request(query)
        if xml and bnf_parse_nb(xml) > 0:
            return xml, strategy
        if xml is None:
            break  # network error — stop trying

    return None, "not_found"


# ---------------------------------------------------------------------------
# Google Books API
# ---------------------------------------------------------------------------

def google_request(params: dict, api_key: str | None) -> dict | None:
    if api_key:
        params["key"] = api_key
    encoded = urllib.parse.urlencode(params)
    _wait()
    try:
        with urllib.request.urlopen(f"{GOOGLE_URL}?{encoded}", timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  [Google error] {e}", file=sys.stderr)
        return None


def google_parse_volume(item: dict) -> dict:
    info = item.get("volumeInfo", {})
    authors_raw = info.get("authors", [])
    authors = []
    for a in authors_raw:
        parts = a.rsplit(" ", 1)
        authors.append(f"{parts[1]}, {parts[0]}" if len(parts) == 2 else a)

    year = None
    pd = info.get("publishedDate", "")
    m = re.search(r"(\d{4})", pd)
    if m:
        year = int(m.group(1))

    ids = info.get("industryIdentifiers", [])
    by_type = {e.get("type"): e.get("identifier") for e in ids}
    isbn = by_type.get("ISBN_13") or by_type.get("ISBN_10")

    return {
        "title": info.get("title", ""),
        "subtitle": info.get("subtitle", ""),
        "authors": authors,
        "publisher": info.get("publisher", ""),
        "year": year,
        "pages": info.get("pageCount"),
        "categories": info.get("categories", []),
        "language": info.get("language", ""),
        "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
        "isbn": isbn.replace("-", "") if isbn else "",
        "description": re.sub(r"<[^>]+>", "", info.get("description", "")),
    }


def google_lookup_isbn(isbn: str, api_key: str | None) -> dict | None:
    """Single Google Books lookup by ISBN. Returns raw API dict."""
    return google_request({"q": f"isbn:{isbn}", "maxResults": "1"}, api_key)


def google_search_title(title: str, lastname: str,
                         api_key: str | None) -> dict | None:
    """Google Books title+author search with langRestrict=fr."""
    qt = clean_query(title)
    ql = clean_query(lastname)
    q = f"intitle:{qt}"
    if ql:
        q += f" inauthor:{ql}"
    return google_request({"q": q, "maxResults": "5", "langRestrict": "fr"}, api_key)


def google_best(orig_title: str, orig_lastname: str,
                data: dict | None, min_score: float = 0.45) -> dict | None:
    if not data or data.get("totalItems", 0) == 0:
        return None
    items = data.get("items", [])
    if not items:
        return None
    scored = []
    for item in items:
        info = item.get("volumeInfo", {})
        found_title = info.get("title", "")
        found_authors = " ".join(info.get("authors", []))
        sc = score_match(orig_title, orig_lastname, found_title, found_authors)
        scored.append((sc, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_sc, best_item = scored[0]
    if best_sc < min_score:
        return None
    result = google_parse_volume(best_item)
    result["_score"] = round(best_sc, 3)
    result["_confidence"] = "high" if best_sc >= 0.75 else "low"
    return result


# ---------------------------------------------------------------------------
# SUDOC SRU API  (catalogue universitaire français, ~15 M notices)
#
# Protocole : même SRU que BNF, format de notice Pica+ (pas UNIMARC).
# Indexes utiles :
#   isb  — ISBN livres       isn  — ISSN périodiques
#   mti  — mots du titre     aut  — mots auteur
#
# BCD API : ces fonctions peuvent être extraites sans modification vers
#           src/bcd_api/services/sudoc_service.py
# ---------------------------------------------------------------------------

def sudoc_request(query: str, max_records: int = 5) -> str | None:
    """Envoie une requête SRU au SUDOC et retourne le XML brut."""
    params = urllib.parse.urlencode({
        "operation":     "searchRetrieve",
        "version":       "1.1",
        "query":         query,
        "maximumRecords": str(max_records),
    })
    _wait()
    try:
        with urllib.request.urlopen(f"{SUDOC_URL}?{params}", timeout=10) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  [SUDOC error] {e}", file=sys.stderr)
        return None


def sudoc_parse_nb(xml_text: str) -> int:
    """Retourne le nombre de notices trouvées dans une réponse SRU SUDOC."""
    try:
        root = ET.fromstring(xml_text)
        for el in root.iter():
            if el.tag.endswith("numberOfRecords") and el.text and el.text.strip():
                return int(el.text.strip())
    except Exception:
        pass
    return 0


def _pica_title(raw: str) -> str:
    """Reconstruit le titre d'affichage depuis l'indicateur de tri Pica+.

    Exemples Pica+ :
      '@Wakou'              → 'Wakou'
      'L' @imagerie ...'   → "L'imagerie ..."
      '@Sa Majesté ...'    → 'Sa Majesté ...'
    """
    if "@" not in raw:
        return raw.strip()
    idx = raw.index("@")
    prefix = raw[:idx].rstrip()   # article non-triant éventuel
    rest   = raw[idx + 1:].strip()
    return (prefix + rest) if prefix else rest


def sudoc_extract_results(xml_text: str) -> list[dict]:
    """Parse les notices Pica+ d'une réponse SRU SUDOC."""
    results = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return results

    def sfs(rec_el, tag: str) -> dict:
        """Retourne {code: valeur} pour le premier datafield du tag donné."""
        for df in rec_el.iter():
            if df.get("tag") == tag:
                return {sf.get("code", ""): sf.text for sf in df if sf.text}
        return {}

    def sfs_all(rec_el, tag: str) -> list[dict]:
        """Retourne la liste de tous les datafields du tag donné."""
        out = []
        for df in rec_el.iter():
            if df.get("tag") == tag:
                out.append({sf.get("code", ""): sf.text for sf in df if sf.text})
        return out

    for rec_data in root.iter():
        if not rec_data.tag.endswith("recordData"):
            continue
        rec = rec_data  # le <record> Pica est un enfant direct

        # Titre (021A livres, 022A périodiques)
        t021 = sfs(rec, "021A")
        t022 = sfs(rec, "022A")
        raw_title = t021.get("a") or t022.get("a") or ""
        title = _pica_title(raw_title)
        responsibility = t021.get("h", "")  # auteur dans le titre livre

        # Auteurs (028A = auteur principal, 028C = autres)
        a028 = sfs(rec, "028A")
        authors = []
        if a028.get("8"):
            authors.append(a028["8"])
        for co in sfs_all(rec, "028C"):
            if co.get("8"):
                authors.append(co["8"])
        if not authors and responsibility:
            authors = [responsibility]

        # Éditeur / date
        e033 = sfs(rec, "033A")
        publisher = e033.get("n", "")
        pub_date  = e033.get("d", "")

        # Année
        y011 = sfs(rec, "011@")
        year = y011.get("a", "")

        # Langue
        l010 = sfs(rec, "010@")
        language = l010.get("a", "")

        # ISBN (004A$B)
        i004 = sfs(rec, "004A")
        isbn = clean_isbn(i004.get("B", "") or i004.get("0", ""))

        # ISSN (005A$0)
        i005 = sfs(rec, "005A")
        issn = i005.get("0", "") or i005.get("e", "")

        # Collection / série (036E)
        s036 = sfs(rec, "036E")
        series = _pica_title(s036.get("a", "")) if s036.get("a") else ""

        results.append({
            "title": title, "authors": authors, "publisher": publisher,
            "pub_date": pub_date, "year": year, "language": language,
            "isbn": isbn, "issn": issn, "series": series,
        })

    return results


def sudoc_best(orig_title: str, orig_lastname: str,
               results: list[dict], min_score: float = 0.40) -> dict | None:
    """Sélectionne la meilleure notice SUDOC par score titre+auteur."""
    if not results:
        return None
    scored = sorted(
        results,
        key=lambda r: score_match(
            orig_title, orig_lastname,
            r["title"], " ".join(r["authors"])
        ),
        reverse=True,
    )
    best = scored[0]
    sc = score_match(orig_title, orig_lastname,
                     best["title"], " ".join(best["authors"]))
    if sc < min_score:
        return None
    best["_score"]      = round(sc, 3)
    best["_confidence"] = "high" if sc >= 0.75 else "low"
    return best


def sudoc_lookup_isbn(isbn: str) -> str | None:
    """Recherche SUDOC par ISBN (index isb). Retourne le XML brut."""
    return sudoc_request(f"isb={isbn}", max_records=1)


def sudoc_lookup_issn(issn: str) -> str | None:
    """Recherche SUDOC par ISSN (index isn). Retourne le XML brut."""
    return sudoc_request(f"isn={issn}", max_records=1)


def sudoc_search_periodical(title: str) -> tuple[str | None, str]:
    """Cherche un périodique par titre (suppression du numéro de fascicule).

    Retourne (xml_brut, stratégie).
    Stratégie : 'sudoc_issn_title'.
    """
    # Supprimer "n° 205", "num. 12", "#3" etc.
    base = ISSUE_STRIP_RE.sub("", title).strip()
    nt   = normalize(base)
    words = [w for w in nt.split() if w not in STOPWORDS and len(w) > 1]
    if not words:
        return None, "not_found"

    # Requête SRU : mti=mot1 and mti=mot2 …
    query = " and ".join(f"mti={w}" for w in words[:4])
    xml = sudoc_request(query, max_records=3)
    if xml and sudoc_parse_nb(xml) > 0:
        return xml, "sudoc_issn_title"
    return None, "not_found"


def sudoc_search_book(title: str, lastname: str) -> tuple[str | None, str]:
    """Cherche un livre par titre + auteur dans SUDOC.

    Retourne (xml_brut, stratégie).
    """
    nt = normalize(title)
    nl = normalize(lastname)
    words = [w for w in nt.split() if w not in STOPWORDS and len(w) > 1]
    if not words:
        return None, "not_found"

    strategies: list[tuple[str, str]] = []
    base_mti = " and ".join(f"mti={w}" for w in words[:4])
    if nl:
        strategies.append((f"{base_mti} and aut={nl}", "sudoc_title+author"))
    strategies.append((base_mti, "sudoc_title"))

    for query, strategy in strategies:
        xml = sudoc_request(query, max_records=5)
        if xml and sudoc_parse_nb(xml) > 0:
            return xml, strategy
        if xml is None:
            break
    return None, "not_found"


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def read_cache_bnf(cache_dir: Path, key: str) -> str | None:
    f = cache_dir / f"{key}.xml"
    return f.read_text(encoding="utf-8") if f.exists() else None


def write_cache_bnf(cache_dir: Path, key: str, content: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.xml").write_text(content, encoding="utf-8")


def read_cache_google(cache_dir: Path, key: str) -> dict | None:
    f = cache_dir / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def write_cache_google(cache_dir: Path, key: str, data: dict | None) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(
        json.dumps(data or {}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def read_cache_sudoc(cache_dir: Path, key: str) -> str | None:
    f = cache_dir / f"{key}.xml"
    return f.read_text(encoding="utf-8") if f.exists() else None


def write_cache_sudoc(cache_dir: Path, key: str, content: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.xml").write_text(content, encoding="utf-8")


CACHE_MISS = "__MISS__"   # sentinel saved to disk when API returned nothing

# In-memory cache for periodical SUDOC results (current run only).
# Maps normalized base title → raw XML (or CACHE_MISS).
# Avoids redundant disk reads and API calls for magazines with many issues.
_periodical_sudoc_mem: dict[str, str] = {}


def _periodical_sudoc_key(title: str) -> str:
    """Cache key for a periodical: normalized title with issue number stripped.

    'J'aime lire n° 75' and 'J'aime lire n° 176' both map to the same key.
    """
    base = ISSUE_STRIP_RE.sub("", title).strip()
    return "period_" + normalize(base).replace(" ", "_")[:60]


def is_cache_miss(xml: str | None) -> bool:
    return xml == CACHE_MISS


def is_google_miss(data: dict | None) -> bool:
    return data is not None and data.get("__miss__") is True


def detect_periodicals(rows: list[dict], min_count: int = 3) -> dict[str, int]:
    """Détecte les périodiques par clustering de titres avec numéro de fascicule.

    Un titre de base (sans numéro) qui apparaît >= min_count fois dans le CSV
    est considéré comme un périodique. Retourne {base_normalisée: nb_exemplaires}.
    """
    counts: dict[str, int] = {}
    for row in rows:
        t = row.get("Titre", "").strip()
        if ISSUE_STRIP_RE.search(t):
            base = normalize(ISSUE_STRIP_RE.sub("", t).strip())
            if base:
                counts[base] = counts.get(base, 0) + 1
    return {base: n for base, n in counts.items() if n >= min_count}


# ---------------------------------------------------------------------------
# Cover images (Open Library)
# ---------------------------------------------------------------------------

def download_cover(isbn: str, covers_dir: Path) -> str:
    """Télécharge la couverture depuis Open Library et la met en cache local.

    Retourne le nom de fichier ('{isbn}.jpg') si une couverture est trouvée,
    ou '' si aucune couverture n'est disponible ou en cas d'erreur.
    Idempotent : retourne le nom de fichier mis en cache s'il existe déjà.
    """
    if not isbn:
        return ""
    covers_dir.mkdir(parents=True, exist_ok=True)
    filepath = covers_dir / f"{isbn}.jpg"
    if filepath.exists():
        return f"{isbn}.jpg"

    # Rate limiting pour Open Library (courtoisie) - seulement pour les vraies requêtes
    _wait()

    url = COVERS_URL.format(isbn=isbn)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BCD-enrich/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            filepath.write_bytes(r.read())
            return f"{isbn}.jpg"
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  [Cover HTTP {e.code}] {isbn}", file=sys.stderr)
    except Exception as e:
        print(f"  [Cover error] {isbn}: {e}", file=sys.stderr)
    return ""


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_row(row: dict, bnf_dir: Path, google_dir: Path, sudoc_dir: Path,
                covers_dir: Path | None, api_key: str | None, stats: dict,
                min_score: float = 0.45, verbose: bool = False,
                detected_periods: dict[str, int] | None = None) -> dict:
    """Enrich a single BiblioPuce row. Returns the enrichment dict."""
    row_start = time.time()
    title     = row.get("Titre", "").strip()
    author    = row.get("Auteur", "").strip()
    lastname  = parse_author_lastname(author) if author else ""
    isbn_raw  = row.get("ISBN", "").strip().strip('"')
    support   = row.get("Support", "").strip()
    key       = cache_key(row)
    is_issn   = bool(ISSN_PATTERN.match(isbn_raw))    # ISSN stocké dans champ ISBN
    has_isbn  = not is_empty(isbn_raw) and not is_issn
    isbn      = clean_isbn(isbn_raw) if has_isbn else ""
    issn_raw  = isbn_raw if is_issn else ""
    is_book   = support == "Livre"
    is_period = support == "Périodique"

    # Détection par clustering : si le titre de base apparaît >= min_count fois
    # avec un numéro de fascicule, on le traite comme un périodique.
    if not is_period and detected_periods:
        base_norm = normalize(ISSUE_STRIP_RE.sub("", title).strip())
        if base_norm and base_norm in detected_periods:
            is_period = True
            is_book   = False

    enrichment: dict = {col: "" for col in ENRICHED_COLUMNS}
    bnf_result    = None
    google_result = None
    sudoc_result  = None
    source        = "not_found"
    bnf_strat     = ""
    google_strat  = ""
    sudoc_strat   = ""

    # --- BNF lookup ---
    t0 = time.time()
    cached_bnf = read_cache_bnf(bnf_dir, key)
    if verbose and cached_bnf is not None:
        print(f"    BNF cache hit ({time.time()-t0:.3f}s)", file=sys.stderr)

    if cached_bnf is not None:
        bnf_xml = None if is_cache_miss(cached_bnf) else cached_bnf
        stats["bnf_cache_hit"] += 1
        bnf_strat = "skipped" if is_period else ("isbn" if has_isbn else "title")
    else:
        if is_period:
            # SUDOC couvre mieux les périodiques — pas la peine d'interroger BNF
            bnf_xml  = None
            bnf_strat = "skipped"
        elif has_isbn:
            bnf_xml   = bnf_lookup_isbn(isbn)
            bnf_strat = "isbn"
            stats["bnf_requests"] += 1
        elif is_book and title:
            bnf_xml, bnf_strat = bnf_search_title(title, lastname)
            stats["bnf_requests"] += 1
        else:
            bnf_xml = None

        write_cache_bnf(bnf_dir, key, bnf_xml or CACHE_MISS)

    if bnf_xml:
        results = bnf_extract_results(bnf_xml)
        if has_isbn and results:
            # ISBN lookup → take first result directly
            bnf_result = results[0] if results else None
            if bnf_result:
                bnf_result["_confidence"] = "high"
                bnf_result["_score"] = 1.0
        else:
            bnf_result = bnf_best(title, lastname, results, min_score=min_score)

        if bnf_result:
            source = "bnf_isbn" if has_isbn else "bnf_title"
            stats["bnf_found"] += 1

    # --- Google Books (skip tous les périodiques — SUDOC est plus adapté) ---
    skip_google = is_period
    if skip_google or is_issn:
        google_strat = "skipped"
    if not skip_google and not is_issn:
        t0 = time.time()
        cached_google = read_cache_google(google_dir, key)
        if verbose and cached_google is not None:
            print(f"    Google cache hit ({time.time()-t0:.3f}s)", file=sys.stderr)

        if cached_google is not None:
            google_data  = None if is_google_miss(cached_google) else cached_google
            stats["google_cache_hit"] += 1
            google_strat = "isbn" if has_isbn else ("title+author" if lastname else "title-only")
        else:
            if has_isbn:
                google_data  = google_lookup_isbn(isbn, api_key)
                google_strat = "isbn"
                stats["google_requests"] += 1
            elif is_book and title:
                google_data  = google_search_title(title, lastname, api_key)
                google_strat = "title+author" if lastname else "title-only"
                stats["google_requests"] += 1
            else:
                google_data  = None

            write_cache_google(google_dir, key,
                               google_data or {"__miss__": True})

        if google_data and google_data.get("totalItems", 0) > 0:
            if has_isbn:
                items = google_data.get("items", [])
                if items:
                    google_result = google_parse_volume(items[0])
                    google_result["_confidence"] = "high"
                    google_result["_score"] = 1.0
            else:
                google_result = google_best(title, lastname, google_data, min_score=min_score)

            if google_result:
                if source == "not_found":
                    source = "google_isbn" if has_isbn else "google_title"
                stats["google_found"] += 1

    # --- SUDOC (troisième source, toujours interrogé) ---
    t0 = time.time()

    # Pour les périodiques sans identifiant, toutes les issues d'un même
    # titre (J'aime lire n° 75, n° 176…) partagent la même notice SUDOC.
    # On utilise donc le titre de base (sans numéro) comme clé de cache.
    if is_period and not has_isbn and not is_issn and title:
        sudoc_cache_key = _periodical_sudoc_key(title)
    else:
        sudoc_cache_key = key

    # 1. Cache mémoire (périodiques uniquement — évite même la lecture disque)
    if sudoc_cache_key in _periodical_sudoc_mem:
        cached_sudoc = _periodical_sudoc_mem[sudoc_cache_key]
        stats["sudoc_cache_hit"] += 1
        if verbose:
            print(f"    SUDOC mem cache hit ({time.time()-t0:.3f}s)", file=sys.stderr)
    else:
        cached_sudoc = read_cache_sudoc(sudoc_dir, sudoc_cache_key)
        if verbose and cached_sudoc is not None:
            print(f"    SUDOC cache hit ({time.time()-t0:.3f}s)", file=sys.stderr)

    if cached_sudoc is not None:
        sudoc_xml = None if is_cache_miss(cached_sudoc) else cached_sudoc
        if sudoc_cache_key not in _periodical_sudoc_mem:
            stats["sudoc_cache_hit"] += 1
        # Peupler le cache mémoire depuis le disque
        _periodical_sudoc_mem[sudoc_cache_key] = cached_sudoc
        # Inférer la stratégie depuis les inputs (déterministe)
        if is_issn:
            sudoc_strat = "issn"
        elif has_isbn:
            sudoc_strat = "isbn"
        elif is_period:
            sudoc_strat = "issn_title"
        else:
            sudoc_strat = "title"
    else:
        sudoc_xml = None

        if is_issn and issn_raw:
            # ISSN détecté dans le champ ISBN → lookup direct
            sudoc_xml    = sudoc_lookup_issn(issn_raw)
            sudoc_strat  = "issn"
            stats["sudoc_requests"] += 1
        elif has_isbn:
            # ISBN standard → lookup par isb=
            sudoc_xml    = sudoc_lookup_isbn(isbn)
            sudoc_strat  = "isbn"
            stats["sudoc_requests"] += 1
        elif is_period and title:
            # Périodique sans identifiant → titre de base → ISSN
            sudoc_xml, sudoc_strat = sudoc_search_periodical(title)
            stats["sudoc_requests"] += 1
        elif is_book and title:
            # Livre sans ISBN → recherche titre + auteur
            sudoc_xml, sudoc_strat = sudoc_search_book(title, lastname)
            stats["sudoc_requests"] += 1

        result_to_cache = sudoc_xml or CACHE_MISS
        write_cache_sudoc(sudoc_dir, sudoc_cache_key, result_to_cache)
        _periodical_sudoc_mem[sudoc_cache_key] = result_to_cache

    if sudoc_xml:
        results = sudoc_extract_results(sudoc_xml)
        if results:
            if is_issn or has_isbn:
                # Lookup par identifiant → premier résultat direct
                sudoc_result = results[0]
                sudoc_result["_confidence"] = "high"
                sudoc_result["_score"] = 1.0
            elif is_period:
                # Titre périodique → meilleur match sur titre de base
                base = ISSUE_STRIP_RE.sub("", title).strip()
                sudoc_result = sudoc_best(base, "", results, min_score=min_score)
            else:
                sudoc_result = sudoc_best(title, lastname, results, min_score=min_score)

        if sudoc_result:
            if source == "not_found":
                if is_issn:
                    source = "sudoc_issn"
                elif has_isbn:
                    source = "sudoc_isbn"
                elif is_period:
                    source = "sudoc_issn_title"
                else:
                    source = "sudoc_title"
            stats["sudoc_found"] += 1

    # --- Build enrichment columns ---
    if bnf_result:
        enrichment["bnf_title"]      = bnf_result["titles"][0] if bnf_result.get("titles") else ""
        enrichment["bnf_subtitle"]   = bnf_result["subtitles"][0] if bnf_result.get("subtitles") else ""
        enrichment["bnf_authors"]    = " ; ".join(bnf_result.get("authors", []))
        enrichment["bnf_publisher"]  = bnf_result["publishers"][0] if bnf_result.get("publishers") else ""
        enrichment["bnf_year"]       = _extract_year(bnf_result.get("dates", []))
        enrichment["bnf_series"]     = bnf_result["series"][0] if bnf_result.get("series") else ""
        enrichment["bnf_series_vol"] = bnf_result["series_vol"][0] if bnf_result.get("series_vol") else ""
        enrichment["bnf_pages"]      = bnf_result["pages"][0] if bnf_result.get("pages") else ""
        enrichment["bnf_dimensions"] = bnf_result["dims"][0] if bnf_result.get("dims") else ""
        enrichment["bnf_language"]   = bnf_result["languages"][0] if bnf_result.get("languages") else ""
        enrichment["bnf_subjects"]   = " | ".join(bnf_result.get("subjects", []))
        enrichment["bnf_description"]= bnf_result["descriptions"][0] if bnf_result.get("descriptions") else ""
        enrichment["bnf_genre"]      = " | ".join(bnf_result.get("genres", []))
        enrichment["bnf_dewey"]      = bnf_result["deweys"][0] if bnf_result.get("deweys") else ""

        found_isbn = _prefer_isbn13(bnf_result.get("isbns", [])) if bnf_result.get("isbns") else ""
        enrichment["isbn_found"]     = found_isbn if found_isbn else isbn
        enrichment["isbn_source"]    = source
        enrichment["isbn_confidence"]= bnf_result.get("_confidence", "high")

    if google_result:
        enrichment["google_title"]    = google_result.get("title", "")
        enrichment["google_subtitle"] = google_result.get("subtitle", "")
        enrichment["google_authors"]  = " ; ".join(google_result.get("authors", []))
        enrichment["google_publisher"]= google_result.get("publisher", "")
        enrichment["google_year"]     = str(google_result["year"]) if google_result.get("year") else ""
        enrichment["google_pages"]    = str(google_result["pages"]) if google_result.get("pages") else ""
        enrichment["google_categories"]= " | ".join(google_result.get("categories", []))
        enrichment["google_language"] = google_result.get("language", "")
        enrichment["google_thumbnail"]   = google_result.get("thumbnail", "")
        enrichment["google_description"]  = google_result.get("description", "")

        if not bnf_result:
            g_isbn = google_result.get("isbn", "")
            enrichment["isbn_found"]      = g_isbn if g_isbn else isbn
            enrichment["isbn_source"]     = source
            enrichment["isbn_confidence"] = google_result.get("_confidence", "high")

    if sudoc_result:
        enrichment["sudoc_title"]     = sudoc_result.get("title", "")
        enrichment["sudoc_authors"]   = " ; ".join(sudoc_result.get("authors", []))
        enrichment["sudoc_publisher"] = sudoc_result.get("publisher", "")
        enrichment["sudoc_year"]      = sudoc_result.get("year", "")
        enrichment["sudoc_isbn"]      = sudoc_result.get("isbn", "")
        enrichment["sudoc_issn"]      = sudoc_result.get("issn", "")
        enrichment["sudoc_language"]  = sudoc_result.get("language", "")
        enrichment["sudoc_series"]    = sudoc_result.get("series", "")

        # Pour les périodiques, l'ISSN devient l'identifiant trouvé
        # Seulement si BNF et Google n'ont pas déjà fourni un identifiant
        if not enrichment.get("isbn_found"):
            if sudoc_result.get("issn"):
                enrichment["isbn_found"]      = sudoc_result["issn"]
                enrichment["isbn_source"]     = source
                enrichment["isbn_confidence"] = sudoc_result.get("_confidence", "high")
            elif sudoc_result.get("isbn"):
                enrichment["isbn_found"]      = sudoc_result["isbn"]
                enrichment["isbn_source"]     = source
                enrichment["isbn_confidence"] = sudoc_result.get("_confidence", "high")

    enrichment["bnf_strategy"]    = bnf_strat
    enrichment["google_strategy"] = google_strat
    enrichment["sudoc_strategy"]  = sudoc_strat

    # --- enriched_* = BNF > Google > SUDOC > original ---
    found_anything = (
        bnf_result is not None
        or google_result is not None
        or sudoc_result is not None
    )

    enrichment["enriched_title"] = (
        enrichment["bnf_title"]
        or enrichment["google_title"]
        or enrichment["sudoc_title"]
        or title
    )
    enrichment["enriched_authors"] = (
        enrichment["bnf_authors"]
        or enrichment["google_authors"]
        or enrichment["sudoc_authors"]
        or author
    )
    enrichment["enriched_publisher"] = (
        enrichment["bnf_publisher"]
        or enrichment["google_publisher"]
        or enrichment["sudoc_publisher"]
        or row.get("Editeur", "").strip()
    )
    enrichment["enriched_year"] = (
        enrichment["bnf_year"]
        or enrichment["google_year"]
        or enrichment["sudoc_year"]
        or row.get("Annee", "").strip()
    )

    enrichment["enriched_medium_type"] = infer_medium_type(
        bnf_result, google_result, sudoc_result, is_issn
    )

    # --- Cote : notation BCD ---
    # Fiction (Dewey 8xx ou pas de Dewey) → notation simple : PREFIX AUT3
    # Documentaires (Dewey 0-7xx, 9xx)   → Dewey + AUT3
    dewey = enrichment.get("bnf_dewey", "").strip()

    # Suffixe auteur : 3 premières lettres du nom de famille normalisées, majuscules
    best_author = (
        (bnf_result.get("authors") or [None])[0] if bnf_result else None
    ) or author
    aut3 = ""
    if best_author:
        m_aut = re.match(r"^([A-Za-zÀ-ÿ]+)", best_author.strip())
        if m_aut:
            aut3 = normalize(m_aut.group(1))[:3].upper()

    # Préfixe simple pour la fiction — depuis enriched_medium_type (déjà calculé)
    # puis Genre BiblioPuce en fallback pour distinguer Roman/Conte/Poésie
    medium = enrichment.get("enriched_medium_type", "")
    genre_src = row.get("Genre", "").strip().lower()

    _MEDIUM_PREFIX = {
        "Bande dessinée": "BD",
        "Album illustré": "A",
        "Manga":          "BD",
        "Conte":          "C",
        "Poème":          "P",
    }
    _GENRE_PREFIX = {
        "romans et nouvelles": "R", "roman": "R",
        "contes": "C", "contes, légendes et folklore": "C",
        "poèmes et comptines": "P", "poésie": "P",
        "album": "A", "albums": "A",
        "bandes dessinées": "BD",
    }
    fiction_prefix = _MEDIUM_PREFIX.get(medium) or _GENRE_PREFIX.get(genre_src, "")

    is_fiction_dewey = dewey.startswith("8") if dewey else False

    if dewey and not is_fiction_dewey:
        # Documentaire → Dewey + auteur
        enrichment["enriched_cote"] = f"{dewey} {aut3}".strip() if aut3 else dewey
    elif fiction_prefix and aut3:
        # Fiction → notation simple (R DUM, BD ACH, A POM…)
        enrichment["enriched_cote"] = f"{fiction_prefix} {aut3}"
    elif dewey and is_fiction_dewey and aut3:
        # Dewey littérature sans genre connu → fallback notation simple générique
        enrichment["enriched_cote"] = f"R {aut3}"
    else:
        enrichment["enriched_cote"] = ""

    if not found_anything:
        stats["not_found"] += 1

    # --- match_score / source_count / needs_review (supervision OpenRefine) ---
    all_results = [r for r in [bnf_result, google_result, sudoc_result] if r]
    source_count = len(all_results)
    if all_results:
        avg = sum(r.get("_score", 1.0) for r in all_results) / source_count
        enrichment["match_score"] = str(round(avg * 100))
    else:
        enrichment["match_score"] = ""
    enrichment["source_count"] = str(source_count) if source_count else "0"

    _TITLE_SOURCES = {"bnf_title", "google_title", "sudoc_title", "sudoc_issn_title"}
    enrichment["needs_review"] = "1" if (
        source in _TITLE_SOURCES
        or enrichment.get("isbn_confidence") == "low"
    ) else "0"

    # --- Cover image (optionnel — désactivé si covers_dir is None) ---
    if covers_dir is not None:
        effective_isbn = enrichment.get("isbn_found") or isbn
        if effective_isbn and not is_issn:
            t0 = time.time()
            covers_dir.mkdir(parents=True, exist_ok=True)
            filepath = covers_dir / f"{effective_isbn}.jpg"
            if filepath.exists():
                enrichment["cover_image"] = f"{effective_isbn}.jpg"
                stats["covers_found"] += 1
                stats["covers_cache_hit"] += 1
                if verbose:
                    print(f"    Cover cache hit ({time.time()-t0:.3f}s)", file=sys.stderr)

    if verbose:
        print(f"    Total row time: {time.time()-row_start:.3f}s", file=sys.stderr)

    return enrichment


def _extract_year(dates: list) -> str:
    for d in dates:
        m = re.search(r"(\d{4})", d)
        if m:
            return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Inventory group acquisition date
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enrichit un CSV BiblioPuce via BNF + Google Books"
    )
    parser.add_argument("input",  help="Fichier CSV BiblioPuce source")
    parser.add_argument("output", help="Fichier CSV enrichi de sortie")
    parser.add_argument("--api-key", default="",
                        help="Clé API Google Books (optionnelle)")
    parser.add_argument("--limit",  type=int, default=0,
                        help="Limiter le traitement à N entrées (test)")
    parser.add_argument("--cache-dir", default="",
                        help="Dossier parent pour bnf_cache/ et google_cache/ "
                             "(défaut : même dossier que le fichier de sortie)")
    parser.add_argument("--covers-dir", default="",
                        help="Dossier de cache des couvertures (défaut : désactivé). "
                             "Exemple : data/covers")
    parser.add_argument("--min-score", type=float, default=0.45,
                        help="Score minimum pour accepter un résultat par titre "
                             "(0.0–1.0, défaut : 0.45). Les lookups ISBN ignorent ce seuil.")

    args = parser.parse_args()

    api_key = args.api_key or None

    input_path  = Path(args.input)
    output_path = Path(args.output)
    cache_base  = Path(args.cache_dir) if args.cache_dir else output_path.parent
    bnf_dir     = cache_base / "bnf_cache"
    google_dir  = cache_base / "google_cache"
    sudoc_dir   = cache_base / "sudoc_cache"
    covers_dir  = Path(args.covers_dir) if args.covers_dir else None

    # Read input
    with open(input_path, "rb") as f:
        raw = f.read()
    for enc in ["windows-1252", "utf-8", "latin-1"]:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    text = text.lstrip("\ufeff")
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
    original_fieldnames = list(rows[0].keys()) if rows else []

    if args.limit:
        rows = rows[:args.limit]

    total = len(rows)
    stats = {
        "bnf_requests": 0,    "bnf_cache_hit": 0,    "bnf_found": 0,
        "google_requests": 0, "google_cache_hit": 0, "google_found": 0,
        "sudoc_requests": 0,  "sudoc_cache_hit": 0,  "sudoc_found": 0,
        "not_found": 0,
        "covers_found": 0,    "covers_cache_hit": 0,
    }

    if api_key is None:
        google_needed = sum(
            1 for r in rows
            if r.get("Support", "").strip() == "Livre"
            and not ISSN_PATTERN.match(r.get("ISBN", "").strip().strip('"'))
        )
        if google_needed > 800:
            print(f"⚠  Sans clé API Google, limite ~1 000 req/jour "
                  f"({google_needed} livres à traiter). "
                  f"Utilisez --api-key pour un run complet.", file=sys.stderr)

    # Détection des périodiques par clustering de titres avant traitement
    detected_periods = detect_periodicals(rows)
    if detected_periods:
        print(f"\nPeriodiques détectés par clustering ({len(detected_periods)} titres) :")
        for base, count in sorted(detected_periods.items(), key=lambda x: -x[1]):
            print(f"  {count:>4}x  {base}")
        print()

    start = time.time()
    output_rows = []

    for i, row in enumerate(rows, 1):
        support = row.get("Support", "").strip()
        label = row.get("Titre", "?")[:40]
        print(f"[{i:>4}/{total}] {support:<12} {label}")

        verbose = (i <= 10)  # Verbose pour les 10 premières lignes
        enrichment = process_row(row, bnf_dir, google_dir, sudoc_dir, covers_dir, api_key, stats,
                                 min_score=args.min_score, verbose=verbose,
                                 detected_periods=detected_periods)
        merged = {**row, **enrichment}
        output_rows.append({k: v for k, v in merged.items() if k is not None})

    # Write output CSV (UTF-8 with BOM for Excel)
    out_fieldnames = original_fieldnames + ENRICHED_COLUMNS
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    # Write Bibliopuce format CSV with enriched values
    bibliopuce_path = output_path.with_stem(output_path.stem + "_bibliopuce")
    bibliopuce_rows = []
    for row in output_rows:
        bibliopuce_row = {**row}  # Copy all original columns

        # --- Champs principaux enrichis ---
        if row.get("enriched_title"):
            bibliopuce_row["Titre"] = row["enriched_title"]
        if row.get("enriched_authors"):
            bibliopuce_row["Auteur"] = row["enriched_authors"]
        if row.get("enriched_publisher"):
            bibliopuce_row["Editeur"] = row["enriched_publisher"]
        if row.get("enriched_year"):
            bibliopuce_row["Annee"] = row["enriched_year"]
        if row.get("isbn_found"):
            bibliopuce_row["ISBN"] = row["isbn_found"]

        # --- Cote (si vide dans la source) ---
        if not bibliopuce_row.get("Cote", "").strip():
            bibliopuce_row["Cote"] = row.get("enriched_cote") or ""

        # --- Champs facultatifs (si vide dans la source) ---
        if not bibliopuce_row.get("SousTitre", "").strip():
            bibliopuce_row["SousTitre"] = (
                row.get("bnf_subtitle") or row.get("google_subtitle") or ""
            )
        if not bibliopuce_row.get("Collection", "").strip():
            bibliopuce_row["Collection"] = row.get("bnf_series") or ""
        if not bibliopuce_row.get("Numero", "").strip():
            bibliopuce_row["Numero"] = row.get("bnf_series_vol") or ""
        if not bibliopuce_row.get("Description", "").strip():
            bibliopuce_row["Description"] = (
                row.get("bnf_description") or row.get("google_description") or ""
            )
        if not bibliopuce_row.get("Taille", "").strip():
            bibliopuce_row["Taille"] = row.get("bnf_pages") or ""
        if not bibliopuce_row.get("Mots-clefs", "").strip():
            bibliopuce_row["Mots-clefs"] = row.get("bnf_subjects") or ""

        # --- Uniformisation Support → vocabulaire BCD ---
        support = bibliopuce_row.get("Support", "").strip()
        genre_lower = bibliopuce_row.get("Genre", "").strip().lower()
        # Genre peut forcer une correction même si Support est déjà rempli
        # (ex: Support="Livre" mais Genre="Revues et magazines" → Périodique)
        genre_override = _GENRE_TO_MEDIUM.get(genre_lower, "")
        if genre_override and genre_override != support:
            support = genre_override
        if not support:
            # 1. Depuis l'enrichissement BNF/Google/SUDOC
            support = row.get("enriched_medium_type", "")
        if not support:
            # 2. Depuis le champ Genre BiblioPuce (cas non-override)
            support = genre_override
        bibliopuce_row["Support"] = support

        # --- Uniformisation Niveau → catalog_levels BCD ---
        niveau = bibliopuce_row.get("Niveau", "").strip()
        niveau_norm = _NIVEAU_MAP.get(niveau.lower(), "")
        if niveau_norm:
            bibliopuce_row["Niveau"] = niveau_norm

        # --- Uniformisation langue BNF (fre/eng) → BCD (fr/en) ---
        lang = bibliopuce_row.get("Langue", "").strip() if "Langue" in bibliopuce_row else ""
        if not lang:
            lang = row.get("bnf_language") or row.get("google_language") or ""
        lang_norm = _LANG_MAP.get(lang.lower(), lang)
        if "Langue" in original_fieldnames:
            bibliopuce_row["Langue"] = lang_norm

        # Original columns + two extra enrichment columns for review
        bibliopuce_rows.append({
            **{k: bibliopuce_row.get(k, "") for k in original_fieldnames},
            "enriched_medium_type": row.get("enriched_medium_type", ""),
            "enriched_cote":        row.get("enriched_cote", ""),
        })

    bibliopuce_fieldnames = original_fieldnames + ["enriched_medium_type", "enriched_cote"]
    with open(bibliopuce_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=bibliopuce_fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(bibliopuce_rows)

    elapsed = time.time() - start
    minutes, seconds = divmod(int(elapsed), 60)

    found_total = stats["bnf_found"] + stats["google_found"] + stats["sudoc_found"]
    print(f"\n{'='*60}")
    print(f"Traités       : {total}")
    print(f"BNF           : {stats['bnf_found']:>5} trouvés "
          f"({stats['bnf_requests']} req + {stats['bnf_cache_hit']} cache)")
    print(f"Google Books  : {stats['google_found']:>5} trouvés "
          f"({stats['google_requests']} req + {stats['google_cache_hit']} cache)")
    print(f"SUDOC         : {stats['sudoc_found']:>5} trouvés "
          f"({stats['sudoc_requests']} req + {stats['sudoc_cache_hit']} cache)")
    print(f"Total trouvés : {found_total:>5} ({100*found_total//total}%)")
    print(f"Non trouvés   : {stats['not_found']:>5}")
    covers_total = stats["covers_found"]
    covers_new   = covers_total - stats["covers_cache_hit"]
    print(f"Couvertures   : {covers_total:>5} ({covers_new} téléchargées, "
          f"{stats['covers_cache_hit']} en cache)")

    print(f"Durée         : {minutes}m{seconds:02d}s")
    print(f"Sortie        : {output_path}")
    print(f"Bibliopuce    : {bibliopuce_path}")
    print(f"Cache BNF     : {bnf_dir}/ ({len(list(bnf_dir.glob('*.xml')))} fichiers)")
    print(f"Cache Google  : {google_dir}/ ({len(list(google_dir.glob('*.json')))} fichiers)")
    sudoc_count = len(list(sudoc_dir.glob('*.xml'))) if sudoc_dir.exists() else 0
    print(f"Cache SUDOC   : {sudoc_dir}/ ({sudoc_count} fichiers)")
    if covers_dir is not None:
        covers_count = len(list(covers_dir.glob('*.jpg'))) if covers_dir.exists() else 0
        print(f"Couvertures   : {covers_dir}/ ({covers_count} fichiers)")
    else:
        print(f"Couvertures   : désactivées")


if __name__ == "__main__":
    main()
