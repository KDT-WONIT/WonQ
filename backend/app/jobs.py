from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from contracts.messages import JobKind

from .auth import Principal
from .config import settings
from .models import Asset, Job
from .operations import MANAGERS, audit_view, get_round, scoped
from .operations_models import AuditRound, Stock
from .schemas import AssetView, ClaimRequest, ClaimResponse, CompleteRequest, JobCreate

LEASE_SECONDS = 120
MAX_ATTEMPTS = 3
TERMINAL_STATES = {"completed", "failed"}


def assets_in(department: str):
    return select(Asset).where(Asset.department == department)


def create_job(session: Session, principal: Principal, request: JobCreate) -> Job:
    if principal.role == "vendor" or (principal.role not in MANAGERS and request.kind != JobKind.CHATBOT):
        raise HTTPException(403, "담당자 권한이 필요합니다.")
    payload = {}
    if request.kind == JobKind.CHATBOT:
        payload["prompt"] = request.prompt
    department = principal.department
    if request.kind == JobKind.INSPECTION and request.audit_id:
        audit = get_round(session, principal, request.audit_id)
        if audit.status not in {"review", "completed"}:
            raise HTTPException(409, "현장 실사를 제출한 뒤 분석할 수 있습니다.")
        payload["audit_id"] = str(audit.id)
        department = audit.department
    elif request.kind == JobKind.INSPECTION:
        query = scoped(select(Asset), Asset.department, principal)
        asset = session.scalar(query.where(Asset.id == request.asset_id))
        if asset is None:
            raise HTTPException(404, "자산을 찾을 수 없습니다.")
        payload["asset_id"] = str(asset.id)
        department = asset.department

    job = Job(kind=request.kind.value, owner_id=principal.sub, department=department, payload=payload)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def build_context(session: Session, job: Job) -> dict:
    context = dict(job.payload)
    scope = assets_in(job.department)
    if job.kind == JobKind.CHATBOT:
        assets = session.scalars(scope.order_by(Asset.code).limit(25))
        context["assets"] = [
            {"code": asset.code, "name": asset.name, "location": asset.location}
            for asset in assets
        ]
    if job.kind == JobKind.REPORT:
        context["asset_count"] = session.scalar(
            select(func.count()).select_from(Asset).where(Asset.department == job.department)
        )
    if job.kind == JobKind.INSPECTION and "audit_id" in job.payload:
        audit = session.get(AuditRound, UUID(job.payload["audit_id"]))
        if audit is None or audit.department != job.department:
            raise HTTPException(409, "실사 회차를 확인할 수 없습니다.")
        context["audit"] = audit_view(audit)["targets"]
        for target in context["audit"]:
            target["id"] = str(target["id"])
    elif job.kind == JobKind.INSPECTION:
        asset = session.scalar(scope.where(Asset.id == UUID(job.payload["asset_id"])))
        context["asset"] = (
            AssetView.model_validate(asset).model_dump(mode="json", exclude={"qr_token"}) if asset else None
        )
    if job.kind == JobKind.MONITORING:
        context["stock"] = [
            {"name": row.name, "location": row.location, "quantity": row.quantity, "safety_stock": row.safety_stock}
            for row in session.scalars(select(Stock).where(Stock.department == job.department))
        ]
    return context


def claim_job(session: Session, request: ClaimRequest) -> ClaimResponse:
    now = datetime.now(timezone.utc)
    if settings.queue_mode == "sqs" and request.job_id is None:
        raise HTTPException(400, "A queue message job_id is required")

    if request.job_id is not None:
        job = session.get(Job, request.job_id, with_for_update=True)
        if job is None or job.kind != request.kind:
            raise HTTPException(404, "Job not found for this queue")
        if job.status in TERMINAL_STATES:
            return ClaimResponse(state="terminal")
        if job.status == "running" and job.lease_expires_at > now:
            return ClaimResponse(state="busy")
    else:
        available = or_(
            Job.status == "queued",
            and_(Job.status == "running", Job.lease_expires_at <= now),
        )
        job = session.scalar(
            select(Job)
            .where(Job.kind == request.kind, available)
            .order_by(Job.created_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return ClaimResponse(state="empty")

    if job.attempts >= MAX_ATTEMPTS:
        job.status = "failed"
        job.result = {"error": "작업 실행 시간을 초과했습니다."}
        session.commit()
        return ClaimResponse(state="terminal")

    job.status = "running"
    job.attempts += 1
    job.lease_token = uuid4()
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    context = build_context(session, job)
    session.commit()
    return ClaimResponse(state="claimed", job_id=job.id, lease_token=job.lease_token, context=context)


def complete_job(session: Session, job_id: UUID, request: CompleteRequest) -> str:
    job = session.get(Job, job_id, with_for_update=True)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status in TERMINAL_STATES and job.lease_token == request.lease_token:
        return job.status

    if (
        job.status != "running"
        or job.lease_token != request.lease_token
        or job.lease_expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(409, "Job lease expired or superseded")

    if request.succeeded:
        job.status = "completed"
        job.result = request.result
    elif job.attempts >= MAX_ATTEMPTS:
        job.status = "failed"
        job.result = request.result
    else:
        job.status = "queued"
    job.lease_expires_at = None
    session.commit()
    return job.status
