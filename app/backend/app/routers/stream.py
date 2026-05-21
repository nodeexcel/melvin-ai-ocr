import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import JobEvent, Project, User

router = APIRouter(prefix="/api/projects", tags=["stream"])

POLL_INTERVAL = 0.5


async def _event_generator(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    last_event_id = 0

    while True:
        result = await db.execute(
            select(JobEvent)
            .where(JobEvent.project_id == project_id, JobEvent.id > last_event_id)
            .order_by(JobEvent.id)
        )
        events = result.scalars().all()

        for event in events:
            payload = json.dumps({
                "step": event.step,
                "message": event.message,
                "progress_pct": event.progress_pct,
                "timestamp": event.created_at.isoformat(),
            })
            yield f"data: {payload}\n\n"
            last_event_id = event.id

        project = await db.get(Project, project_id)
        if project is None or project.status in ("done", "failed"):
            yield f"data: {json.dumps({'step': 'complete', 'status': project.status if project else 'failed', 'progress_pct': 100})}\n\n"
            return

        await asyncio.sleep(POLL_INTERVAL)


@router.get("/{project_id}/stream")
async def stream_progress(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return StreamingResponse(
        _event_generator(project_id, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
