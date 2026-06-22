"""
API-layer tests for template download endpoints:
- GET /api/v1/catalog/template
- GET /api/v1/borrowers/template
"""

import pytest
from fastapi.testclient import TestClient
from src.bcd_api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_catalog_template_endpoint(client):
    """Verify that the catalog template endpoint returns the expected CSV."""
    response = client.get("/api/v1/catalog/template")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "catalog_dublin_core_template.csv" in response.headers["content-disposition"]
    
    # Check some column headers are present in the response
    content = response.text
    assert "dc.title" in content
    assert "dc.identifier" in content
    assert "item.id" in content

def test_borrowers_template_endpoint(client):
    """Verify that the borrowers template endpoint returns the expected CSV."""
    response = client.get("/api/v1/borrowers/template")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "borrowers_template.csv" in response.headers["content-disposition"]
    
    # Check some column headers are present in the response
    content = response.text
    assert "borrower_id" in content
    assert "first_name" in content
    assert "last_name" in content
    assert "class" in content
