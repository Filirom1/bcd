"""API boundary tests for Find a notice and source configuration."""

import pytest
from fastapi.testclient import TestClient

from src.bcd_api.core.deps import get_db
from src.bcd_api.main import app
from src.bcd_api.models.bibliographic_record import BibliographicRecord


@pytest.fixture
def catalog_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def test_local_notice_search_endpoint_is_database_only(catalog_client, db_session, monkeypatch):
    record = BibliographicRecord(
        title="Wapiti", isbn="issn:0984-2314", medium_type="Périodique"
    )
    db_session.add(record)
    db_session.commit()
    monkeypatch.setattr(
        "src.bcd_api.services.external.sudoc.search_by_issn",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("external call")),
    )

    response = catalog_client.get("/api/v1/catalog/notices/search", params={"q": "Wapiti"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Wapiti"
    assert body["external_sources"] == []


def test_lookup_endpoint_accepts_one_explicit_source(catalog_client, monkeypatch):
    monkeypatch.setattr(
        "src.bcd_api.api.v1.catalog.catalog_service.lookup_notice_source",
        lambda db, query, source: {
            "status": "found", "source": source, "data": {"title": "Book"}
        },
    )

    response = catalog_client.post(
        "/api/v1/catalog/notices/lookup",
        json={"query": "9782123456789", "source": "bnf"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "bnf"


def test_external_source_configuration_endpoint_returns_all_fixed_sources(catalog_client):
    response = catalog_client.get("/api/v1/catalog/external-sources")

    assert response.status_code == 200
    assert [source["source"] for source in response.json()["sources"]] == [
        "bnf", "google_books", "sudoc"
    ]
    assert response.json()["sources"][0]["timeout"] == 4
