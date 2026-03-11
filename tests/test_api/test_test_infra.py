import pytest

from app.database import get_session
from app.main import app

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


async def test_api_client_fixture_applies_session_override(api_client):
    assert get_session in app.dependency_overrides

    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
