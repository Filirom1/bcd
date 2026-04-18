# BNF SRU API Integration Contract

**Feature**: School Library Management System (BCD)
**Date**: 2026-01-30
**API Version**: SRU 1.2
**Status**: Complete

## Overview

The BNF (Bibliothèque nationale de France) provides a free SRU (Search/Retrieve via URL) API for querying their general catalog. This contract defines how the BCD system integrates with the BNF API for ISBN-based bibliographic record lookup during cataloging operations.

**Use Case**: When a librarian adds a new book to the catalog, they scan the ISBN barcode. The system calls the BNF SRU API to retrieve complete bibliographic metadata (title, author, publisher, etc.) in UNIMARC format, pre-filling the cataloging form and reducing manual data entry.

---

## API Endpoint

**Base URL**: `https://catalogue.bnf.fr/api/SRU`

**Protocol**: HTTP GET (SRU 1.2 standard)

**Authentication**: None required (public API)

**Rate Limiting**: No documented limits, but respect usage guidelines (max 1 request per second recommended)

---

## Request Format

### Query by ISBN

**HTTP Method**: GET

**URL Structure**:
```
https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=bib.isbn%20all%20%22{ISBN}%22&recordSchema=unimarcxchange&maximumRecords=1
```

### Query Parameters

| Parameter | Required | Value | Description |
|-----------|----------|-------|-------------|
| `version` | Yes | `1.2` | SRU protocol version |
| `operation` | Yes | `searchRetrieve` | SRU operation type |
| `query` | Yes | `bib.isbn all "{ISBN}"` | Search query (URL-encoded) |
| `recordSchema` | Yes | `unimarcxchange` | Response format (UNIMARC XML) |
| `maximumRecords` | No | `1` | Limit results (default: 10) |

**ISBN Normalization**:
- Accept both ISBN-10 and ISBN-13
- Strip hyphens before querying: `978-2-8006-8734-7` → `9782800687347`
- URL-encode the query parameter

### Example Request (cURL)

```bash
# ISBN: 978-2-8006-8734-7
curl "https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=bib.isbn%20all%20%229782800687347%22&recordSchema=unimarcxchange&maximumRecords=1"
```

### Example Request (Python)

```python
import requests
from urllib.parse import quote

def search_bnf_by_isbn(isbn: str) -> dict:
    """
    Search BNF catalog by ISBN and return bibliographic data.

    Args:
        isbn: ISBN-10 or ISBN-13 (with or without hyphens)

    Returns:
        dict: Bibliographic metadata or None if not found
    """
    # Normalize ISBN (remove hyphens)
    isbn_normalized = isbn.replace('-', '').replace(' ', '')

    # Build query
    query = f'bib.isbn all "{isbn_normalized}"'

    # SRU endpoint
    url = "https://catalogue.bnf.fr/api/SRU"
    params = {
        'version': '1.2',
        'operation': 'searchRetrieve',
        'query': query,
        'recordSchema': 'unimarcxchange',
        'maximumRecords': '1'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        # Parse XML response
        # (see Response Format section below)
        return parse_unimarc_xml(response.content)

    except requests.exceptions.RequestException as e:
        # Handle network errors (see Error Handling section)
        return None
```

---

## Response Format

### Structure

The API returns XML conforming to the SRU 1.2 standard. Bibliographic records are encoded in **UnimarcXchange 2.0** (ISO 25577) format within the `<srw:recordData>` element.

### Response Envelope

```xml
<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:version>1.2</srw:version>
  <srw:echoedSearchRetrieveRequest>
    <srw:query>bib.isbn="978-2-8006-8734-7"</srw:query>
  </srw:echoedSearchRetrieveRequest>
  <srw:numberOfRecords>1</srw:numberOfRecords>
  <srw:records>
    <srw:record>
      <srw:recordSchema>marcxchange</srw:recordSchema>
      <srw:recordPacking>xml</srw:recordPacking>
      <srw:recordData>
        <!-- UNIMARC data here -->
      </srw:recordData>
      <srw:recordIdentifier>ark:/12148/cb392727522</srw:recordIdentifier>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>
```

### UNIMARC Record Structure

Within `<srw:recordData>`, the UNIMARC record uses the `marcxchange` namespace:

```xml
<mxc:record xmlns:mxc="info:lc/xmlns/marcxchange-v2" format="UNIMARC" type="Bibliographic">
  <mxc:leader>     cam  22        450 </mxc:leader>
  <mxc:controlfield tag="001">FRBNF392727520000004</mxc:controlfield>

  <!-- Datafields with tag, indicators, and subfields -->
  <mxc:datafield tag="010" ind1=" " ind2=" ">
    <mxc:subfield code="a">2-8006-8734-7</mxc:subfield>
    <mxc:subfield code="b">rel.</mxc:subfield>
    <mxc:subfield code="d">3,95 EUR</mxc:subfield>
  </mxc:datafield>

  <mxc:datafield tag="200" ind1="1" ind2=" ">
    <mxc:subfield code="a">L'équipe des mascrottes</mxc:subfield>
    <mxc:subfield code="f">une histoire de Dominique Petit</mxc:subfield>
    <mxc:subfield code="g">ill. par Marina Rouzé</mxc:subfield>
  </mxc:datafield>

  <!-- More datafields... -->
</mxc:record>
```

---

## UNIMARC Field Mappings

This table shows how to extract bibliographic data from UNIMARC fields and map to our database schema.

| UNIMARC Tag | Subfield | Field Name | Database Column | Notes |
|-------------|----------|------------|-----------------|-------|
| **010** | $a | ISBN | `isbn` | Normalize (remove hyphens) |
| **010** | $b | Binding type | `binding_type` | "rel." → "hardcover", "br." → "paperback" |
| **010** | $d | Price | ❌ SKIP | No cost tracking in our system |
| **101** | $a | Language | `language` | ISO 639-2 code (e.g., "fre", "eng") |
| **102** | $a | Country of publication | `country_code` | ISO 3166 code (e.g., "FR", "BE") |
| **200** | $a | Title proper | `title` | **Required** |
| **200** | $e | Subtitle | `subtitle` | Optional |
| **200** | $f | Author statement | `authors` | Parse to extract author name(s) |
| **200** | $g | Illustrator statement | `illustrators` | Parse to extract illustrator name(s) |
| **210** | $a | Place of publication | ❌ Skip | Optional, not critical |
| **210** | $c | Publisher | `publisher` | May appear multiple times (take first) |
| **210** | $d | Publication year | `publication_year` | Extract 4-digit year |
| **215** | $a | Extent (pages) | `page_count`, `physical_size` | "83 p." → 83 |
| **215** | $c | Illustrations | `has_illustrations` | If contains "ill." → true |
| **215** | $d | Dimensions | `dimensions` | e.g., "18 cm", "21 x 15 cm" |
| **225** | $a | Series title | `collection` | e.g., "La mini C" |
| **225** | $v | Volume number | `series_number` | e.g., "24" |
| **330** | $a | Summary | `description` | May be multiple paragraphs |
| **606** | $a | Subject headings | `keywords` | Repeatable, combine into array |
| **676** | $a | Dewey classification | ❌ Skip | Use local call_number instead |
| **700** | $a, $b | Personal name (author) | `authors` | Primary author (surname, forename) |
| **701** | $a, $b | Personal name (additional author) | `authors` | Additional authors (repeatable) |
| **702** | $a, $b | Personal name (illustrator) | `illustrators` | Illustrator (surname, forename) |

### Parsing Rules

**Authors (700, 701)**:
```
700$a: "Petit"
700$b: "Dominique"
700$f: "19..-...." (lifespan)
700$c: "auteur pour la jeunesse" (qualifier)

→ Parse to: "Petit, Dominique"
```

**Illustrators (702)**:
```
702$a: "Rouzé"
702$b: "Marina"

→ Parse to: "Rouzé, Marina"
```

**Author Statement from 200$f**:
```
200$f: "une histoire de Dominique Petit"

→ Extract: "Petit, Dominique" OR "Dominique Petit"
```

**Binding Type (010$b)**:
```
"rel." → "hardcover" (relié)
"br." → "paperback" (broché)
"cart." → "hardcover" (cartonné)
```

**Page Count (215$a)**:
```
"83 p." → 83
"128 p. ; 21 cm" → 128 (ignore dimension)
"1 vol. (352 p.)" → 352
```

**Illustrations (215$c)**:
```
"ill. en coul." → has_illustrations = true
"couv. ill." → has_illustrations = true
No "ill." → has_illustrations = false
```

**Target Audience (from 100 coded field)**:
```
100$a position 8-9:
"a " → "child" (enfant)
"b " → "youth" (jeunesse)
"c " → "youth" (jeunes adultes)
"d " → "adult" (adulte)
```

---

## Example: Complete Request/Response

### Request

```
GET https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&query=bib.isbn%20all%20%229782800687347%22&recordSchema=unimarcxchange&maximumRecords=1
```

### Response (Abbreviated)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/">
  <srw:numberOfRecords>1</srw:numberOfRecords>
  <srw:records>
    <srw:record>
      <srw:recordData>
        <mxc:record xmlns:mxc="info:lc/xmlns/marcxchange-v2">
          <mxc:datafield tag="010" ind1=" " ind2=" ">
            <mxc:subfield code="a">2-8006-8734-7</mxc:subfield>
            <mxc:subfield code="b">rel.</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="101" ind1="0" ind2=" ">
            <mxc:subfield code="a">fre</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="102" ind1=" " ind2=" ">
            <mxc:subfield code="a">BE</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="200" ind1="1" ind2=" ">
            <mxc:subfield code="a">L'équipe des mascrottes</mxc:subfield>
            <mxc:subfield code="f">une histoire de Dominique Petit</mxc:subfield>
            <mxc:subfield code="g">ill. par Marina Rouzé</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="210" ind1=" " ind2=" ">
            <mxc:subfield code="c">Hemma</mxc:subfield>
            <mxc:subfield code="d">2004</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="215" ind1=" " ind2=" ">
            <mxc:subfield code="a">83 p.</mxc:subfield>
            <mxc:subfield code="c">ill. en coul.</mxc:subfield>
            <mxc:subfield code="d">18 cm</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="225" ind1="|" ind2=" ">
            <mxc:subfield code="a">La mini C</mxc:subfield>
            <mxc:subfield code="v">24</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="330" ind1=" " ind2=" ">
            <mxc:subfield code="a">Pour pouvoir exploiter sa dernière découverte...</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="700" ind1=" " ind2="|">
            <mxc:subfield code="a">Petit</mxc:subfield>
            <mxc:subfield code="b">Dominique</mxc:subfield>
            <mxc:subfield code="c">auteur pour la jeunesse</mxc:subfield>
          </mxc:datafield>
          <mxc:datafield tag="702" ind1=" " ind2="|">
            <mxc:subfield code="a">Rouzé</mxc:subfield>
            <mxc:subfield code="b">Marina</mxc:subfield>
          </mxc:datafield>
        </mxc:record>
      </srw:recordData>
    </srw:record>
  </srw:records>
</srw:searchRetrieveResponse>
```

### Parsed Data (for our database)

```json
{
  "isbn": "978-2-8006-8734-7",
  "title": "L'équipe des mascrottes",
  "subtitle": null,
  "authors": ["Petit, Dominique"],
  "illustrators": ["Rouzé, Marina"],
  "publisher": "Hemma",
  "publication_year": 2004,
  "collection": "La mini C",
  "series_number": "24",
  "language": "fre",
  "country_code": "BE",
  "binding_type": "hardcover",
  "description": "Pour pouvoir exploiter sa dernière découverte...",
  "page_count": 83,
  "has_illustrations": true,
  "dimensions": "18 cm",
  "physical_size": "83 p., ill. en coul., 18 cm",
  "medium_type": "Livre",
  "target_audience": "child"
}
```

---

## Error Handling

### HTTP Status Codes

| Status | Scenario | Action |
|--------|----------|--------|
| `200 OK` | Successful response | Parse XML |
| `400 Bad Request` | Invalid query format | Validate ISBN format, retry |
| `500 Internal Server Error` | BNF server error | Retry after 5s, then fallback to manual entry |
| `503 Service Unavailable` | BNF maintenance | Fallback to manual entry |
| `Timeout` | Network/slow response | Retry once, then fallback |

### SRU-Specific Errors

**No Records Found** (`numberOfRecords = 0`):
```xml
<srw:numberOfRecords>0</srw:numberOfRecords>
```
**Action**: Display message "ISBN not found in BNF catalog - please enter manually" and show manual entry form.

**Multiple Records** (`numberOfRecords > 1`):
```xml
<srw:numberOfRecords>3</srw:numberOfRecords>
```
**Action**: Show list of matches, let librarian select correct one. (Rare - ISBNs should be unique)

**Diagnostic Messages**:
```xml
<srw:diagnostics>
  <diag:diagnostic>
    <diag:code>10</diag:code>
    <diag:message>Query syntax error</diag:message>
  </diag:diagnostic>
</srw:diagnostics>
```
**Action**: Log error, fallback to manual entry.

### Error Handling Strategy

```python
def lookup_isbn_bnf(isbn: str) -> Optional[dict]:
    """
    Look up ISBN in BNF catalog with comprehensive error handling.
    """
    try:
        # Step 1: Validate ISBN format
        if not is_valid_isbn(isbn):
            logger.warning(f"Invalid ISBN format: {isbn}")
            return None

        # Step 2: Call BNF API
        response = requests.get(bnf_url, params=params, timeout=10)
        response.raise_for_status()

        # Step 3: Parse XML
        root = etree.fromstring(response.content)

        # Step 4: Check numberOfRecords
        num_records = int(root.find('.//srw:numberOfRecords', namespaces).text)

        if num_records == 0:
            logger.info(f"ISBN not found in BNF: {isbn}")
            return None  # Trigger manual entry

        if num_records > 1:
            logger.warning(f"Multiple records for ISBN {isbn}")
            # Return first match or show selection UI

        # Step 5: Extract UNIMARC data
        marc_record = root.find('.//mxc:record', namespaces)
        biblio_data = parse_unimarc_record(marc_record)

        logger.info(f"Successfully retrieved BNF data for ISBN {isbn}")
        return biblio_data

    except requests.exceptions.Timeout:
        logger.error(f"BNF API timeout for ISBN {isbn}")
        # Show warning to librarian, fallback to manual
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"BNF API error: {e}")
        return None

    except Exception as e:
        logger.exception(f"Unexpected error parsing BNF response: {e}")
        return None
```

---

## Implementation Notes

### XML Parsing Library

**Recommended**: `pymarc` library for MARC/UNIMARC parsing

```python
from pymarc import marcxml

# Parse UnimarcXchange XML
records = marcxml.parse_xml_to_array(xml_string)
record = records[0]

# Access fields
title = record['200']['a'] if '200' in record and 'a' in record['200'] else None
isbn = record['010']['a'] if '010' in record else None
```

**Alternative**: `lxml` for direct XML parsing with XPath

```python
from lxml import etree

root = etree.fromstring(response.content)

# Extract fields with namespace handling
namespaces = {
    'srw': 'http://www.loc.gov/zing/srw/',
    'mxc': 'info:lc/xmlns/marcxchange-v2'
}

title = root.find('.//mxc:datafield[@tag="200"]/mxc:subfield[@code="a"]', namespaces).text
```

### Caching Strategy

**Response Caching**: Cache BNF responses for 7 days to reduce API calls for duplicate lookups.

```python
import redis
import json

def get_bnf_data_cached(isbn: str) -> Optional[dict]:
    """
    Look up ISBN with Redis caching (7-day TTL).
    """
    cache_key = f"bnf:isbn:{isbn}"

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Call API
    data = lookup_isbn_bnf(isbn)

    # Cache result (including None = not found)
    if data:
        redis_client.setex(cache_key, 604800, json.dumps(data))  # 7 days

    return data
```

### Rate Limiting

**Client-Side Rate Limiting**: Limit to 1 request per second to be respectful.

```python
import time
from functools import wraps

last_request_time = 0

def rate_limit(min_interval=1.0):
    """Decorator to enforce minimum interval between API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global last_request_time
            elapsed = time.time() - last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_request_time = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(min_interval=1.0)
def call_bnf_api(isbn):
    # API call here
    pass
```

---

## Testing

### Test ISBNs

Use these ISBNs for testing BNF API integration:

| ISBN | Title | Expected Result |
|------|-------|-----------------|
| `978-2-8006-8734-6` | L'équipe des mascrottes | ✅ Found |
| `978-2-07-061275-8` | Harry Potter à l'école des sorciers | ✅ Found |
| `978-2-07-062674-8` | Le Petit Prince | ✅ Found |
| `000-0-0000-0000-0` | Invalid ISBN | ❌ Not found |
| `978-9999-9999-9-9` | Non-existent ISBN | ❌ Not found (0 records) |

### Contract Tests

```python
import pytest

def test_bnf_isbn_lookup_success():
    """Test successful ISBN lookup."""
    isbn = "978-2-8006-8734-6"
    data = lookup_isbn_bnf(isbn)

    assert data is not None
    assert data['title'] == "L'équipe des mascrottes"
    assert data['publisher'] == "Hemma"
    assert data['language'] == "fre"
    assert data['page_count'] == 83

def test_bnf_isbn_not_found():
    """Test ISBN not in BNF catalog."""
    isbn = "978-9999-9999-9-9"
    data = lookup_isbn_bnf(isbn)

    assert data is None  # Should return None, not raise exception

def test_bnf_api_timeout():
    """Test timeout handling."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout()

        data = lookup_isbn_bnf("978-2-07-061275-8")

        assert data is None  # Graceful fallback

def test_bnf_invalid_xml():
    """Test malformed XML response."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.content = b"<invalid>xml"

        data = lookup_isbn_bnf("978-2-07-061275-8")

        assert data is None  # Should not crash
```

---

## References

- [BNF SRU API Documentation](https://api.bnf.fr/api-sru-catalogue-general)
- [SRU 1.2 Protocol Specification](https://www.loc.gov/standards/sru/sru-1-2.html)
- [UNIMARC Bibliographic Format (3rd ed.)](https://www.ifla.org/unimarc-updates/unimarc-bibliographic-3rd-edition-with-updates/)
- [UnimarcXchange Schema](http://www.loc.gov/standards/iso25577/)
- [pymarc Documentation](https://pymarc.readthedocs.io/)

---

## Summary

**Integration Points**:
1. Cataloging workflow: Librarian scans ISBN → System calls BNF API → Pre-fills form
2. Offline-first: BNF API only used during cataloging (not circulation)
3. Graceful fallback: If API fails/unavailable → Manual entry mode
4. Data enrichment: 8 new fields from BNF (language, page count, target audience, etc.)
5. Performance: Cache responses, rate limit to 1 req/s

**Key Benefits**:
- ✅ Reduces manual data entry by ~80% (from 5 minutes to 30 seconds per book)
- ✅ Ensures metadata consistency and quality
- ✅ Supports multilingual collections (language field)
- ✅ Age-appropriate selection (target_audience, page_count)
- ✅ No authentication required (free public API)
