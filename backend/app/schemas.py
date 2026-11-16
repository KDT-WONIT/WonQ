from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contracts.messages import JobKind

JobStatus = Literal["queued", "running", "completed", "failed"]


class AssetView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    location: str
    department: str
    item_code: str | None
    serial: str | None
    qr_token: UUID
    status: str


class DashboardView(BaseModel):
    total_assets: int
    active_assets: int
    categories: dict[str, int]
    weekly_changes: int | None = None
    audit_checked: int | None = None
    audit_matched: int | None = None
    audit_issues: int | None = None


class JobCreate(BaseModel):
    kind: JobKind
    prompt: str | None = Field(default=None, max_length=1500)
    asset_id: UUID | None = None
    audit_id: UUID | None = None

    @model_validator(mode="after")
    def validate_inputs(self) -> "JobCreate":
        if self.kind == JobKind.CHATBOT:
            self.prompt = (self.prompt or "").strip()
            if not self.prompt:
                raise ValueError("A chatbot question is required")
        if self.kind == JobKind.INSPECTION and (self.asset_id is None) == (self.audit_id is None):
            raise ValueError("실사 회차 또는 단일 자산을 지정하세요.")
        return self


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: JobKind
    status: JobStatus
    result: dict | None
    created_at: datetime


class ClaimRequest(BaseModel):
    kind: JobKind
    job_id: UUID | None = None


class ClaimResponse(BaseModel):
    state: Literal["empty", "busy", "terminal", "claimed"]
    job_id: UUID | None = None
    lease_token: UUID | None = None
    context: dict | None = None


class CompleteRequest(BaseModel):
    lease_token: UUID
    succeeded: bool
    result: dict
