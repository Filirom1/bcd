#!/usr/bin/env python3
"""Download book cover images from multiple APIs in cascade.

Reads an enriched CSV (output of enrich_bibliopuce.py) and attempts to download
a cover image for each book from the following sources in order:

  1. google_direct  -- google_thumbnail URL already present in the CSV
  2. amazon         -- direct URL at images-na.ssl-images-amazon.com (ISBN-10 = ASIN)
  3. openlibrary    -- covers.openlibrary.org (prefers ISBN-13)
  4. google_api     -- googleapis.com/books (API key recommended to avoid 503s)
  5. geobib         -- couverture.geobib.fr (BNF proxy, ISBN-13)

All requests are cached (hits and misses) so the script is idempotent:
re-running it will not repeat requests already made.

Usage:
    python scripts/download_covers.py Table_enrichie.csv
    python scripts/download_covers.py Table_enrichie.csv --covers-dir data/covers
    python scripts/download_covers.py Table_enrichie.csv --google-key AIza...
    python scripts/download_covers.py Table_enrichie.csv --limit 100 --verbose
"""

import argparse
import csv
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RATE_INTERVAL = 1.1       # seconds between live network requests
MIN_IMAGE_BYTES = 3_000   # images smaller than this are placeholders / 1x1 pixels

MISS_SENTINEL = "__MISS__"

AMAZON_HOSTS = [
    "images-na.ssl-images-amazon.com",
    "m.media-amazon.com",
]
# LZZZZZZZ ~ 326x500 px (large), TZZZZZZZ ~ 70x110 px (tiny thumbnail)
AMAZON_SUFFIXES = ["LZZZZZZZ", "TZZZZZZZ"]

HEADERS = {
    "User-Agent": "BCD-covers/1.0 (school library; contact: bcd@ecole.fr)",
    "Accept": "image/jpeg,image/png,image/*",
}

APIS = ["google_direct", "amazon", "openlibrary", "google_api", "geobib"]

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

_last_request: float = 0.0


def _wait() -> None:
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < RATE_INTERVAL:
        time.sleep(RATE_INTERVAL - elapsed)
    _last_request = time.time()


# ---------------------------------------------------------------------------
# ISBN-10 / ISBN-13 conversion
# ---------------------------------------------------------------------------

def isbn10_to_isbn13(isbn10: str) -> str:
    if len(isbn10) != 10:
        return isbn10
    base = "978" + isbn10[:9]
    total = sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(base))
    check = (10 - (total % 10)) % 10
    return base + str(check)


def isbn13_to_isbn10(isbn13: str) -> str | None:
    if len(isbn13) != 13 or not isbn13.startswith("978"):
        return None
    base = isbn13[3:12]
    total = sum((10 - i) * int(d) for i, d in enumerate(base))
    check = (11 - (total % 11)) % 11
    return base + ("X" if check == 10 else str(check))


def both_forms(isbn: str) -> tuple[str | None, str | None]:
    """Return (isbn10, isbn13) for any input ISBN."""
    isbn = isbn.strip().replace("-", "").replace(" ", "")
    if len(isbn) == 10:
        return isbn, isbn10_to_isbn13(isbn)
    if len(isbn) == 13:
        return isbn13_to_isbn10(isbn), isbn
    return None, None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _api_cache_dir(cache_dir: Path, api: str) -> Path:
    d = cache_dir / api
    d.mkdir(parents=True, exist_ok=True)
    return d


def _is_miss(cache_dir: Path, api: str, isbn: str) -> bool:
    return (_api_cache_dir(cache_dir, api) / f"{isbn}.miss").exists()


def _mark_miss(cache_dir: Path, api: str, isbn: str) -> None:
    (_api_cache_dir(cache_dir, api) / f"{isbn}.miss").touch()


def _cached_image(cache_dir: Path, api: str, isbn: str) -> Path | None:
    d = _api_cache_dir(cache_dir, api)
    for ext in (".jpg", ".png", ".gif"):
        p = d / f"{isbn}{ext}"
        if p.exists():
            return p
    return None


def _save_image(cache_dir: Path, api: str, isbn: str, data: bytes) -> Path:
    p = _api_cache_dir(cache_dir, api) / f"{isbn}.jpg"
    p.write_bytes(data)
    return p


def _json_cache(cache_dir: Path, api: str, isbn: str) -> Path:
    return _api_cache_dir(cache_dir, api) / f"{isbn}.json"


# ---------------------------------------------------------------------------
# Generic image fetch
# ---------------------------------------------------------------------------

def _fetch_image(url: str, verbose: bool = False) -> bytes | None:
    """Download an image URL. Returns bytes or None on failure / too small."""
    _wait()
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
            ct = r.headers.get("Content-Type", "")
            if "image" in ct and len(data) >= MIN_IMAGE_BYTES:
                return data
            if verbose:
                print(f"    [image] too small or wrong type ({len(data)}B, {ct})")
    except urllib.error.HTTPError as e:
        if verbose and e.code != 404:
            print(f"    [image] HTTP {e.code} {url[:70]}")
    except Exception as e:
        if verbose:
            print(f"    [image] error: {e}")
    return None


# ---------------------------------------------------------------------------
# API 1: google_direct -- URL already in the CSV
# ---------------------------------------------------------------------------

def try_google_direct(isbn: str, thumbnail_url: str, cache_dir: Path,
                      verbose: bool = False) -> Path | None:
    api = "google_direct"
    if not thumbnail_url or _is_miss(cache_dir, api, isbn):
        return None
    cached = _cached_image(cache_dir, api, isbn)
    if cached:
        return cached

    url = thumbnail_url.replace("http://", "https://")
    data = _fetch_image(url, verbose)
    if data:
        return _save_image(cache_dir, api, isbn, data)
    _mark_miss(cache_dir, api, isbn)
    return None


# ---------------------------------------------------------------------------
# API 2: amazon -- direct URL (unofficial but effective for French books)
# ---------------------------------------------------------------------------

def try_amazon(isbn: str, cache_dir: Path, verbose: bool = False) -> Path | None:
    """Amazon cover via direct URL. Uses ISBN-10 (= ASIN for books)."""
    api = "amazon"
    if _is_miss(cache_dir, api, isbn):
        return None
    cached = _cached_image(cache_dir, api, isbn)
    if cached:
        return cached

    isbn10, _ = both_forms(isbn)
    if not isbn10:
        _mark_miss(cache_dir, api, isbn)
        return None

    for suffix in AMAZON_SUFFIXES:
        for host in AMAZON_HOSTS:
            url = f"https://{host}/images/P/{isbn10}.01.{suffix}.jpg"
            data = _fetch_image(url, verbose)
            if data:
                return _save_image(cache_dir, api, isbn, data)

    _mark_miss(cache_dir, api, isbn)
    return None


# ---------------------------------------------------------------------------
# API 3: openlibrary -- covers.openlibrary.org
# ---------------------------------------------------------------------------

def try_openlibrary(isbn: str, cache_dir: Path, verbose: bool = False) -> Path | None:
    api = "openlibrary"
    if _is_miss(cache_dir, api, isbn):
        return None
    cached = _cached_image(cache_dir, api, isbn)
    if cached:
        return cached

    isbn10, isbn13 = both_forms(isbn)
    for try_isbn in filter(None, [isbn13, isbn10]):
        url = f"https://covers.openlibrary.org/b/isbn/{try_isbn}-M.jpg?default=false"
        data = _fetch_image(url, verbose)
        if data:
            return _save_image(cache_dir, api, isbn, data)

    _mark_miss(cache_dir, api, isbn)
    return None


# ---------------------------------------------------------------------------
# API 4: google_api -- googleapis.com/books
# ---------------------------------------------------------------------------

def try_google_api(isbn: str, cache_dir: Path, api_key: str | None = None,
                   verbose: bool = False) -> Path | None:
    """Google Books REST API. Use an API key to avoid 503 rate-limit errors."""
    api = "google_api"
    if _is_miss(cache_dir, api, isbn):
        return None
    cached = _cached_image(cache_dir, api, isbn)
    if cached:
        return cached

    _, isbn13 = both_forms(isbn)
    lookup = isbn13 or isbn

    json_path = _json_cache(cache_dir, api, isbn)
    data = None
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text("utf-8"))
            if data.get(MISS_SENTINEL):
                return None
        except json.JSONDecodeError:
            data = None

    if data is None:
        params = f"q=isbn:{lookup}&maxResults=1"
        if api_key:
            params += f"&key={api_key}"
        url = f"https://www.googleapis.com/books/v1/volumes?{params}"
        _wait()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            json_path.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
        except Exception as e:
            if verbose:
                print(f"    [google_api] error: {e}")
            _mark_miss(cache_dir, api, isbn)
            return None

    if not data or data.get("totalItems", 0) == 0 or not data.get("items"):
        json_path.write_text(json.dumps({MISS_SENTINEL: True}), "utf-8")
        _mark_miss(cache_dir, api, isbn)
        return None

    links = data["items"][0].get("volumeInfo", {}).get("imageLinks", {})
    for size in ["large", "medium", "small", "thumbnail", "smallThumbnail"]:
        if size in links:
            thumb_url = links[size].replace("http://", "https://")
            img_data = _fetch_image(thumb_url, verbose)
            if img_data:
                return _save_image(cache_dir, api, isbn, img_data)

    json_path.write_text(json.dumps({MISS_SENTINEL: True}), "utf-8")
    _mark_miss(cache_dir, api, isbn)
    return None


# ---------------------------------------------------------------------------
# API 5: geobib -- couverture.geobib.fr (BNF proxy)
# ---------------------------------------------------------------------------

def try_geobib(isbn: str, cache_dir: Path, verbose: bool = False) -> Path | None:
    """geobib.fr: converts ISBN -> BNF ARK -> cover image."""
    api = "geobib"
    if _is_miss(cache_dir, api, isbn):
        return None
    cached = _cached_image(cache_dir, api, isbn)
    if cached:
        return cached

    _, isbn13 = both_forms(isbn)
    if not isbn13:
        _mark_miss(cache_dir, api, isbn)
        return None

    url = f"https://couverture.geobib.fr/api/v1/{isbn13}/medium"
    data = _fetch_image(url, verbose)
    if data:
        return _save_image(cache_dir, api, isbn, data)

    _mark_miss(cache_dir, api, isbn)
    return None


# ---------------------------------------------------------------------------
# Cascade
# ---------------------------------------------------------------------------

def download_cover(isbn: str, thumbnail_url: str, covers_dir: Path,
                   cache_dir: Path, api_key: str | None = None,
                   verbose: bool = False) -> tuple[Path | None, str | None]:
    """
    Try all APIs in cascade until a cover is found.

    Returns (dest_path, api_name) on success, or (None, None) if nothing found.
    dest_path is the final file in covers_dir (e.g. data/covers/{isbn}.jpg).
    """
    isbn = isbn.strip().replace("-", "").replace(" ", "")
    if not isbn:
        return None, None

    dest = covers_dir / f"{isbn}.jpg"
    if dest.exists():
        return dest, "cached"

    fns = {
        "google_direct": lambda: try_google_direct(isbn, thumbnail_url, cache_dir, verbose),
        "amazon":        lambda: try_amazon(isbn, cache_dir, verbose),
        "openlibrary":   lambda: try_openlibrary(isbn, cache_dir, verbose),
        "google_api":    lambda: try_google_api(isbn, cache_dir, api_key, verbose),
        "geobib":        lambda: try_geobib(isbn, cache_dir, verbose),
    }

    for api in APIS:
        if api == "google_direct" and not thumbnail_url:
            continue
        cached_path = fns[api]()
        if cached_path:
            covers_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cached_path, dest)
            return dest, api

    return None, None


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def get_isbn(row: dict) -> str:
    for col in ("isbn_found", "ISBN"):
        v = row.get(col, "").strip().strip('"')
        if v:
            return v
    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download book cover images from multiple APIs."
    )
    parser.add_argument("input_csv", help="Enriched CSV (Table_enrichie.csv or output.csv)")
    parser.add_argument("--covers-dir", default="data/covers",
                        help="Output directory for cover images (default: data/covers)")
    parser.add_argument("--cache-dir", default="covers_cache",
                        help="Per-API cache directory (default: covers_cache)")
    parser.add_argument("--google-key", default=os.environ.get("GOOGLE_KEY"),
                        help="Google Books API key (or set GOOGLE_KEY env var)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only N rows (0 = all)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    covers_dir = Path(args.covers_dir)
    cache_dir = Path(args.cache_dir)
    covers_dir.mkdir(parents=True, exist_ok=True)

    if args.google_key:
        print(f"Google API key: {args.google_key[:8]}...OK")

    # Stats
    hits_by_api: dict[str, int] = {api: 0 for api in APIS}
    total = 0
    already_had = 0
    no_isbn = 0
    covered = 0
    per_isbn: list[dict] = []

    print(f"Reading {args.input_csv}...")
    with open(args.input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if args.limit:
        rows = rows[: args.limit]
    total = len(rows)
    print(f"{total} rows to process\n")

    for i, row in enumerate(rows, 1):
        isbn = get_isbn(row)
        thumbnail_url = row.get("google_thumbnail", "").strip()
        existing = row.get("cover_image", "").strip()

        if not isbn:
            no_isbn += 1
            continue

        dest = covers_dir / f"{isbn}.jpg"
        if existing and dest.exists():
            already_had += 1
            covered += 1
            per_isbn.append({"isbn": isbn, "title": row.get("Titre", ""),
                              "api": "pre-existing", "file": str(dest)})
            continue

        if args.verbose or i % 200 == 0:
            pct = covered / max(i, 1) * 100
            print(f"[{i}/{total}] {isbn}  {row.get('Titre', '')[:40]}"
                  f"  (covered so far: {covered}/{i}, {pct:.0f}%)")

        path, api = download_cover(
            isbn, thumbnail_url, covers_dir, cache_dir,
            api_key=args.google_key, verbose=args.verbose,
        )

        if path:
            covered += 1
            if api and api != "cached":
                hits_by_api[api] = hits_by_api.get(api, 0) + 1
        per_isbn.append({"isbn": isbn, "title": row.get("Titre", ""),
                          "api": api or "none", "file": str(path or "")})

    # ---------------------------------------------------------------------------
    # Final report
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print(" Cover Download Report")
    print("=" * 60)
    print(f"  Total rows          : {total}")
    print(f"  No ISBN             : {no_isbn}")
    print(f"  Already had cover   : {already_had}")
    print(f"  Processed this run  : {total - no_isbn - already_had}")
    print()
    print("  Hits by API (this run):")
    for api in APIS:
        h = hits_by_api.get(api, 0)
        bar = "#" * h if h < 50 else "#" * 50 + f"(+{h-50})"
        print(f"    {api:<16} : {h:>5}  {bar}")
    print()
    total_with_isbn = total - no_isbn
    pct = covered / total_with_isbn * 100 if total_with_isbn else 0
    print(f"  Total covered       : {covered}/{total_with_isbn} ({pct:.1f}%)")
    print(f"  Still missing       : {total_with_isbn - covered}/{total_with_isbn}")
    print("=" * 60)

    # Save per-ISBN CSV
    stats_path = Path("cover_stats.csv")
    with open(stats_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["isbn", "title", "api", "file"])
        writer.writeheader()
        writer.writerows(per_isbn)

    print(f"\nPer-ISBN stats : {stats_path}")
    print(f"Covers         : {covers_dir.absolute()}")
    print(f"Cache          : {cache_dir.absolute()}")


if __name__ == "__main__":
    main()
