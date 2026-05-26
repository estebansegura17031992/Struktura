# tests/integration/test_health.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """El endpoint /health debe retornar 200 con db conectada."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_check_structure(client: AsyncClient):
    """El response debe tener exactamente los campos esperados."""
    response = await client.get("/health")
    data = response.json()
    assert set(data.keys()) == {"status", "db", "timestamp"}
