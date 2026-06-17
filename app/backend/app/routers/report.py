import asyncio
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import AnalysisResult, Project, RateSheet, User
from app.pipeline.cost_estimate import estimate_costs
from app.report.generator import generate_report

router = APIRouter(prefix="/api/projects", tags=["report"])


@router.get("/{project_id}/cost-estimate")
async def get_cost_estimate(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the preliminary cost estimate for a project using the user's saved rates."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project or project.status != "done":
        return {}

    ar_result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.project_id == project_id)
    )
    analysis = ar_result.scalar_one_or_none()
    if not analysis:
        return {}

    rs_result = await db.execute(select(RateSheet).where(RateSheet.user_id == current_user.id))
    rate_sheet = rs_result.scalar_one_or_none()
    rates = rate_sheet.rates if rate_sheet else {}

    return estimate_costs(analysis.raw_json, rates)


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

    # Load user's rate sheet (if any) and compute cost estimate
    rs_result = await db.execute(select(RateSheet).where(RateSheet.user_id == current_user.id))
    rate_sheet = rs_result.scalar_one_or_none()
    rates = rate_sheet.rates if rate_sheet else {}
    cost_estimate = estimate_costs(analysis.raw_json, rates)

    if not analysis.report_pdf_path or not os.path.exists(analysis.report_pdf_path):
        pdf_path = f"{project.file_path}_report.pdf"
        data = {**analysis.raw_json, "cost_estimate": cost_estimate}
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_report, data, pdf_path)
        analysis.report_pdf_path = pdf_path
        await db.commit()
    else:
        pdf_path = analysis.report_pdf_path

    safe_name = re.sub(r"[^\w\-.]", "_", project.name) + "_estimate.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=safe_name,
    )
