import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_user, verify_password


@pytest.mark.asyncio
async def test_login_returns_token(client: AsyncClient, db_session: AsyncSession):
    await create_user(db_session, "melvin", "password123")
    await db_session.commit()

    response = await client.post("/api/auth/login", json={"username": "melvin", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    await create_user(db_session, "melvin", "password123")
    await db_session.commit()

    response = await client.post("/api/auth/login", json={"username": "melvin", "password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    response = await client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    assert response.status_code == 401
