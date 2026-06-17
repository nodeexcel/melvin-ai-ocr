from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import AnalysisResult, Project, RateSheet, User

router = APIRouter(prefix="/api/rates", tags=["rates"])


class RatesPayload(BaseModel):
    # Labor
    wall_stud_labor: float = 0
    plywood_subfloor_labor: float = 0
    plywood_sheathing_labor: float = 0
    tji_joist_labor: float = 0
    concrete_labor: float = 0
    excavation_labor: float = 0
    hardware_install: float = 0
    # Equipment
    concrete_pump_per_cy: float = 0
    crane_per_sqft: float = 0
    scaffold_per_sqft: float = 0


@router.get("")
async def get_rates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(RateSheet).where(RateSheet.user_id == current_user.id))
    sheet = result.scalar_one_or_none()
    return sheet.rates if sheet else {}


@router.put("")
async def save_rates(
    payload: RatesPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(RateSheet).where(RateSheet.user_id == current_user.id))
    sheet = result.scalar_one_or_none()
    rates = payload.model_dump(exclude_none=True)

    if sheet:
        sheet.rates = rates
    else:
        sheet = RateSheet(user_id=current_user.id, rates=rates)
        db.add(sheet)

    await db.commit()

    # Invalidate cached PDFs so next download regenerates with new rates
    user_projects = await db.execute(
        select(Project).where(Project.user_id == current_user.id)
    )
    for project in user_projects.scalars().all():
        ar = await db.execute(
            select(AnalysisResult).where(AnalysisResult.project_id == project.id)
        )
        analysis = ar.scalar_one_or_none()
        if analysis and analysis.report_pdf_path:
            analysis.report_pdf_path = None
    await db.commit()

    return {"saved": True, "rates": rates}
