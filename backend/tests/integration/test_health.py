"""Tests de integración — health check (R-0804)."""
import pytest
 
 
@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data
    assert data["db"] == "connected"
 
 
@pytest.mark.asyncio
async def test_health_sin_autenticacion(client):
    """El health check es público — no requiere token."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
 
 
@pytest.mark.asyncio
async def test_endpoint_protegido_sin_token(client):
    """Un endpoint protegido sin token debe retornar 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "TOKEN_INVALID"
