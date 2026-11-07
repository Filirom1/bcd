"""Integration coverage for the Find a notice routing contract."""

from unittest.mock import Mock

import pytest

from src.bcd_api.core.exceptions import ValidationError
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.models.system_settings import SystemSettings
from src.bcd_api.schemas.item import ItemCreate
from src.bcd_api.services.catalog.commands import create_item
from src.bcd_api.services.catalog.notice_lookup import (
    lookup_identifier_cascade,
    lookup_notice_source,
    search_local_notices,
    source_configuration,
)
from src.bcd_api.services.catalog.notice_lookup import (
    test_external_source as run_external_source_test,
)
from src.bcd_api.utils.catalog_input import classify_catalog_input


def make_record(db, **values):
    record = BibliographicRecord(
        title=values.get("title", "Book"),
        isbn=values.get("isbn"),
        medium_type=values.get("medium_type", "Livre"),
        publisher=values.get("publisher"),
        publication_year=values.get("publication_year"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_search_local_notice_does_not_call_external_sources(db_session, monkeypatch):
    """A matching local notice is returned before any provider is considered."""
    record = make_record(
        db_session,
        title="Wapiti",
        isbn="issn:0984-2314",
        medium_type="Périodique",
        publisher="Milan",
    )
    db_session.add_all(
        [
            Item(item_id="W-1", bibliographic_record_id=record.id, call_number="414"),
            Item(item_id="W-2", bibliographic_record_id=record.id, call_number="440"),
        ]
    )
    db_session.commit()
    external = Mock(side_effect=AssertionError("local lookup must not call a provider"))
    monkeypatch.setattr("src.bcd_api.services.external.bnf.search_by_isbn", external)
    monkeypatch.setattr("src.bcd_api.services.external.google_books.search_by_isbn", external)
    monkeypatch.setattr("src.bcd_api.services.external.sudoc.search_by_issn", external)

    items, total, classified = search_local_notices(db_session, "Wapiti")

    assert total == 1
    assert items[0]["notice_id"] == record.id
    assert items[0]["publisher"] == "Milan"
    assert items[0]["issues_present"] == ["414", "440"]
    assert classified.kind == "text"
    external.assert_not_called()


def test_unsupported_press_barcode_is_not_an_identifier():
    classified = classify_catalog_input("3780237306003")

    assert classified.kind == "unsupported_barcode"
    assert classified.identifier_type is None
    assert classified.external_sources == []


def test_free_text_routes_to_all_three_external_catalogs():
    classified = classify_catalog_input("Le Petit Prince")

    assert classified.kind == "text"
    assert classified.external_sources == ["bnf", "google_books", "sudoc"]
    assert classify_catalog_input(" ").external_sources == []


def test_search_by_title_after_unsupported_barcode_finds_local_notice(db_session):
    make_record(db_session, title="Wapiti", isbn="issn:0984-2314", medium_type="Périodique")

    first, total, classified = search_local_notices(db_session, "3780237306003")
    results, title_total, title_classified = search_local_notices(db_session, "Wapiti")

    assert first == []
    assert total == 0
    assert classified.kind == "unsupported_barcode"
    assert title_total == 1
    assert results[0]["title"] == "Wapiti"
    assert title_classified.kind == "text"


def test_title_search_ignores_case_accents_spaces_and_hyphens(db_session):
    sorciere = make_record(db_session, title="La Sorcière")
    magazine = make_record(db_session, title="J-Magazine")

    without_accent, _, _ = search_local_notices(db_session, "sorciere")
    with_different_case, _, _ = search_local_notices(db_session, "SORCIÈRE")
    with_space, _, _ = search_local_notices(db_session, "j magazine")
    with_hyphen, _, _ = search_local_notices(db_session, "J-MAGAZINE")

    assert [item["notice_id"] for item in without_accent] == [sorciere.id]
    assert [item["notice_id"] for item in with_different_case] == [sorciere.id]
    assert [item["notice_id"] for item in with_space] == [magazine.id]
    assert [item["notice_id"] for item in with_hyphen] == [magazine.id]


def test_isbn_tries_bnf_then_google_and_never_sudoc(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.bcd_api.services.external.bnf.search_by_isbn",
        lambda value, timeout: calls.append(("bnf", value, timeout)) or None,
    )
    monkeypatch.setattr(
        "src.bcd_api.services.external.google_books.search_by_isbn",
        lambda value, timeout: calls.append(("google_books", value, timeout))
        or {"title": "Found book", "isbn": value},
    )
    monkeypatch.setattr(
        "src.bcd_api.services.external.sudoc.search_by_issn",
        lambda *args, **kwargs: calls.append(("sudoc", args, kwargs))
        or {"title": "Must not be used"},
    )

    result = lookup_identifier_cascade(db_session, "9782123456789")

    assert result["title"] == "Found book"
    assert [call[0] for call in calls] == ["bnf", "google_books"]
    assert calls[0][2] == 2
    assert calls[1][2] == 2


def test_isbn_skips_external_metadata_without_title_and_uses_google(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.bcd_api.services.external.bnf.search_by_isbn",
        lambda value, timeout: calls.append("bnf")
        or {"authors": ["Gérald Stehr"], "cover_url": "https://books.example/cover.jpg"},
    )
    monkeypatch.setattr(
        "src.bcd_api.services.external.google_books.search_by_isbn",
        lambda value, timeout: calls.append("google_books")
        or {"title": "Fouines à peur du noir", "isbn": value},
    )

    result = lookup_identifier_cascade(db_session, "9782211053150")

    assert result["title"] == "Fouines à peur du noir"
    assert calls == ["bnf", "google_books"]


def test_issn_uses_sudoc_only(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.bcd_api.services.external.bnf.search_by_isbn",
        lambda *args, **kwargs: calls.append("bnf") or {"title": "wrong"},
    )
    monkeypatch.setattr(
        "src.bcd_api.services.external.google_books.search_by_isbn",
        lambda *args, **kwargs: calls.append("google_books") or {"title": "wrong"},
    )
    monkeypatch.setattr(
        "src.bcd_api.services.external.sudoc.search_by_issn",
        lambda value, timeout: calls.append(("sudoc", value, timeout))
        or {"title": "Wapiti", "issn": value},
    )

    result = lookup_identifier_cascade(db_session, "0984-2314")

    assert result["title"] == "Wapiti"
    assert calls == [("sudoc", "0984-2314", 3)]


def test_ean977_extracts_issn_and_uses_local_or_sudoc(db_session, monkeypatch):
    make_record(db_session, title="Wapiti", isbn="issn:1144-1658", medium_type="Périodique")
    sudoc = Mock(return_value={"title": "Unexpected external result"})
    monkeypatch.setattr("src.bcd_api.services.external.sudoc.search_by_issn", sudoc)

    local = lookup_identifier_cascade(db_session, "9771144165005")

    assert local["title"] == "Wapiti"
    sudoc.assert_not_called()

    db_session.query(BibliographicRecord).delete()
    db_session.commit()
    sudoc.return_value = {"title": "Wapiti", "issn": "1144-1658"}

    external = lookup_identifier_cascade(db_session, "9771144165005")

    assert external["title"] == "Wapiti"
    sudoc.assert_called_once_with("1144-1658", timeout=3)


def test_source_configuration_uses_shorter_default_timeouts(db_session):
    sources = source_configuration(db_session)

    assert {source["source"]: source["timeout"] for source in sources} == {
        "bnf": 2,
        "google_books": 2,
        "sudoc": 3,
    }


def test_disabled_source_is_not_called(db_session, monkeypatch):
    settings = db_session.query(SystemSettings).first()
    settings.bnf_enabled = False
    db_session.commit()
    provider = Mock(side_effect=AssertionError("disabled provider called"))
    monkeypatch.setattr("src.bcd_api.services.external.bnf.search_by_isbn", provider)

    result = lookup_notice_source(db_session, "9782123456789", "bnf")

    assert result["status"] == "disabled"
    provider.assert_not_called()


def test_source_timeout_setting_is_forwarded(db_session, monkeypatch):
    settings = db_session.query(SystemSettings).first()
    settings.bnf_timeout = 11
    db_session.commit()
    provider = Mock(return_value=None)
    monkeypatch.setattr("src.bcd_api.services.external.bnf.search_by_isbn", provider)

    lookup_notice_source(db_session, "9782123456789", "bnf")

    provider.assert_called_once_with("9782123456789", timeout=11)


def test_text_lookup_returns_candidates_from_requested_source(db_session, monkeypatch):
    candidates = [
        {"title": "Le Petit Prince", "cover_url": "https://books.example/cover.jpg"},
        {"title": "Le Petit Prince illustré"},
    ]
    provider = Mock(return_value=candidates)
    monkeypatch.setattr(
        "src.bcd_api.services.external.bnf.search_by_title",
        provider,
    )

    result = lookup_notice_source(db_session, "Le Petit Prince", "bnf")

    assert result["status"] == "results"
    assert result["source"] == "bnf"
    assert result["total"] == 2
    assert result["items"][0]["cover_url"] == "https://books.example/cover.jpg"
    assert all(item["_source"] == "bnf" for item in result["items"])
    provider.assert_called_once_with("Le Petit Prince", timeout=2, limit=10)


@pytest.mark.parametrize(
    ("source", "provider_path"),
    [
        ("bnf", "src.bcd_api.services.external.bnf.search_by_title"),
        ("google_books", "src.bcd_api.services.external.google_books.search_by_text"),
        ("sudoc", "src.bcd_api.services.external.sudoc.search_by_text"),
    ],
)
def test_text_lookup_dispatches_to_each_external_provider(
    db_session, monkeypatch, source, provider_path
):
    candidate = {"title": "Le Petit Prince"}
    if source == "sudoc":
        candidate.update({"issn": "1163-7706", "medium_type": "Périodique"})
    provider = Mock(return_value=[candidate])
    monkeypatch.setattr(provider_path, provider)

    result = lookup_notice_source(db_session, "Le Petit Prince", source)

    assert result["status"] == "results"
    assert result["items"][0]["_source"] == source
    if source == "sudoc":
        assert result["items"][0]["isbn"] == "issn:1163-7706"
        assert result["items"][0]["identifier_type"] == "issn"
    provider.assert_called_once_with(
        "Le Petit Prince", timeout={"bnf": 2, "google_books": 2, "sudoc": 3}[source], limit=10
    )


def test_text_lookup_returns_remote_candidates_even_when_local_match_exists(
    db_session, monkeypatch
):
    record = make_record(db_session, title="Le Petit Prince")
    provider = Mock(return_value=[{"title": "Le Petit Prince nouvelle édition"}])
    monkeypatch.setattr(
        "src.bcd_api.services.external.bnf.search_by_title",
        provider,
    )

    result = lookup_notice_source(db_session, "Le Petit Prince", "bnf")
    local_items, local_total, _ = search_local_notices(db_session, "Le Petit Prince")

    assert local_total == 1
    assert local_items[0]["notice_id"] == record.id
    assert result["status"] == "results"
    assert result["items"][0]["title"] == "Le Petit Prince nouvelle édition"
    provider.assert_called_once_with("Le Petit Prince", timeout=2, limit=10)


def test_settings_test_button_calls_configured_source(db_session, monkeypatch):
    settings = db_session.query(SystemSettings).first()
    settings.sudoc_timeout = 9
    db_session.commit()
    provider = Mock(return_value={"title": "Wapiti"})
    monkeypatch.setattr("src.bcd_api.services.external.sudoc.search_by_issn", provider)

    result = run_external_source_test(db_session, "sudoc", "1163-7706")

    assert result["ok"] is True
    assert result["status"] == "reachable"
    provider.assert_called_once_with("1163-7706", timeout=9)


def test_periodical_item_requires_and_stores_explicit_issue_in_call_number(db_session):
    record = make_record(
        db_session, title="Wapiti", isbn="issn:0984-2314", medium_type="Périodique"
    )

    with pytest.raises(ValidationError):
        create_item(db_session, ItemCreate(item_id="BCD-1", bibliographic_record_id=record.id))

    item = create_item(
        db_session,
        ItemCreate(item_id="BCD-1", bibliographic_record_id=record.id, call_number="440"),
    )

    assert item.call_number == "440"
    assert item.item_id == "BCD-1"
