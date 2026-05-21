import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import AnalysisResult, Project, User
from app.report.generator import generate_report

router = APIRouter(prefix="/api/projects", tags=["report"])


@router.get("/{project_id}/report")
async def download_report(
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
    if project.status != "done":
        raise HTTPException(status_code=400, detail="Analysis not complete")

    ar_result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.project_id == project_id)
    )
    analysis = ar_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis results not found")

    if not analysis.report_pdf_path:
        pdf_path = f"{project.file_path}_report.pdf"
        generate_report(analysis.raw_json, pdf_path)
        analysis.report_pdf_path = pdf_path
        await db.commit()
    else:
        pdf_path = analysis.report_pdf_path

    safe_name = f"{project.name.replace(' ', '_')}_estimate.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=safe_name,
    )
