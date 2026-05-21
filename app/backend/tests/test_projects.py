import io
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, db_session: AsyncSession):
    await create_user(db_session, "melvin", "pass123")
    await db_session.commit()
    r = await client.post("/api/auth/login", json={"username": "melvin", "password": "pass123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_projects_empty(client: AsyncClient, auth_headers):
    r = await client.get("/api/projects", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_upload_creates_project(client: AsyncClient, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.projects._executor", None)
    monkeypatch.setattr("app.routers.projects._submit_pipeline", lambda *a, **kw: None)
    monkeypatch.setattr("app.config.settings.upload_dir", str(tmp_path))

    pdf_bytes = b"%PDF-1.4 fake pdf content"
    r = await client.post(
        "/api/projects/upload",
        headers=auth_headers,
        data={"name": "Test Project"},
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "pending"
    assert data["name"] == "Test Project"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, auth_headers):
    r = await client.get("/api/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_requires_auth(client: AsyncClient):
    r = await client.get("/api/projects")
    assert r.status_code in (401, 403)
