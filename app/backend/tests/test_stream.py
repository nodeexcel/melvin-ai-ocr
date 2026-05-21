import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_user
from app.models import JobEvent, Project


@pytest.mark.asyncio
async def test_stream_returns_events(client: AsyncClient, db_session: AsyncSession):
    user = await create_user(db_session, "melvin2", "pass")
    await db_session.flush()

    project = Project(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Test",
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        status="done",
    )
    db_session.add(project)
    await db_session.flush()

    event = JobEvent(
        project_id=project.id,
        step="classifying",
        message="Found 10 pages",
        progress_pct=20,
    )
    db_session.add(event)
    await db_session.commit()

    r = await client.post("/api/auth/login", json={"username": "melvin2", "password": "pass"})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/projects/{project.id}/stream", headers=headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
