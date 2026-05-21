import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Project, User
from app.pipeline.runner import pipeline_worker
from app.schemas import ProjectDetail, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])
_executor = None  # initialized via lifespan in main.py


def _submit_pipeline(project_id: str, pdf_path: str, db_sync_url: str, openai_api_key: str) -> None:
    _executor.submit(
        pipeline_worker,
        project_id,
        pdf_path,
        settings.upload_dir,
        db_sync_url,
        openai_api_key,
    )


@router.post("/upload", response_model=ProjectOut)
async def upload_project(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    project_id = uuid.uuid4()
    safe_filename = f"{project_id}_{Path(file.filename).name}"
    file_path = upload_dir / safe_filename

    content = await file.read()
    file_path.write_bytes(content)

    project = Project(
        id=project_id,
        user_id=current_user.id,
        name=name,
        original_filename=file.filename,
        file_path=str(file_path),
        status="pending",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    _submit_pipeline(
        project_id=str(project.id),
        pdf_path=str(file_path),
        db_sync_url=settings.database_sync_url,
        openai_api_key=settings.openai_api_key,
    )

    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.result))
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    out = ProjectDetail.model_validate(project)

    if project.result:
        out.raw_json = project.result.raw_json
        # Map filesystem path to download URL
        if project.result.report_pdf_path:
            out.report_pdf_url = f"/api/projects/{project_id}/report"

    return out


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.result))
        .where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.file_path:
        Path(project.file_path).unlink(missing_ok=True)
    if project.result and project.result.report_pdf_path:
        Path(project.result.report_pdf_path).unlink(missing_ok=True)

    await db.delete(project)
    await db.commit()
