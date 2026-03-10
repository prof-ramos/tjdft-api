"""Test main application endpoints"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.api

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns correct response"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "TJDFT API"
    assert data["version"] == "0.1.0"
    assert "docs" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
