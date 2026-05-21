import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as _app_database
from app.database import get_db
from app.deps import get_current_user
from app.models import JobEvent, Project, User

router = APIRouter(prefix="/api/projects", tags=["stream"])

POLL_INTERVAL = 0.5
MAX_STREAM_SECONDS = 600


@asynccontextmanager
async def _session_context(session: Optional[AsyncSession]):
    """Yield the provided session as-is, or open a new one from AsyncSessionLocal."""
    if session is not None:
        yield session
    else:
        async with _app_database.AsyncSessionLocal() as db:
            yield db


async def _event_generator(
    project_id: uuid.UUID,
    request: Request,
    _db: Optional[AsyncSession] = None,
) -> AsyncGenerator[str, None]:
    deadline = time.monotonic() + MAX_STREAM_SECONDS
    last_event_id = 0

    async with _session_context(_db) as db:
        while True:
            if time.monotonic() > deadline:
                yield f"data: {json.dumps({'step': 'timeout', 'status': 'failed', 'progress_pct': 0})}\n\n"
                return
            if await request.is_disconnected():
                return

            # Fetch new events
            events_result = await db.execute(
                select(JobEvent)
                .where(JobEvent.project_id == project_id, JobEvent.id > last_event_id)
                .order_by(JobEvent.id)
            )
            events = events_result.scalars().all()

            for event in events:
                payload = json.dumps({
                    "step": event.step,
                    "message": event.message,
                    "progress_pct": event.progress_pct,
                    "timestamp": event.created_at.isoformat(),
                })
                yield f"data: {payload}\n\n"
                last_event_id = event.id

            # Re-query status directly — bypasses identity map cache
            status_result = await db.execute(
                select(Project.status).where(Project.id == project_id)
            )
            status = status_result.scalar_one_or_none()
            if status is None or status in ("done", "failed"):
                yield f"data: {json.dumps({'step': 'complete', 'status': status or 'failed', 'progress_pct': 100})}\n\n"
                return

            await asyncio.sleep(POLL_INTERVAL)


@router.get("/{project_id}/stream")
async def stream_progress(
    project_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ownership check with the request-scoped session (short-lived)
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Pass no _db so the generator opens its own long-lived session via AsyncSessionLocal.
    # This avoids both the identity-map cache bug and the closed-session bug that occur
    # when the request-scoped `db` session is reused inside the generator.
    return StreamingResponse(
        _event_generator(project_id, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
