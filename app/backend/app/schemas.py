import uuid
from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    name: str


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    original_filename: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectOut):
    raw_json: dict | None = None
    report_pdf_path: str | None = None


class JobEventOut(BaseModel):
    id: int
    step: str
    message: str
    progress_pct: int
    created_at: datetime

    model_config = {"from_attributes": True}
