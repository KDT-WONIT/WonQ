from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .auth import DemoRole, Principal, create_dev_token, get_principal, require_worker
from .db import get_session
from .jobs import claim_job, complete_job, create_job
from .models import Asset, Job
from .operations import MANAGERS, compare_target, scoped
from .operations_models import AuditRound, AuditTarget, Movement
from .operations_routes import router as operations_router
from .reference_models import Item
from .schemas import AssetView, ClaimRequest, ClaimResponse, CompleteRequest, DashboardView, JobCreate, JobView

app = FastAPI(title="WONIT API", version="0.1.0")
api = APIRouter(prefix="/api")
internal = APIRouter(prefix="/internal/worker", dependencies=[Depends(require_worker)])
Database = Annotated[Session, Depends(get_session)]
User = Annotated[Principal, Depends(get_principal)]


@api.get("/health")
def health(session: Database):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


class DemoLogin(BaseModel):
    role: DemoRole = "asset_manager"


@api.post("/auth/dev-token")
def dev_token(data: DemoLogin | None = None):
    return {"access_token": create_dev_token(data.role if data else "asset_manager"), "token_type": "bearer"}


@api.get("/auth/me", response_model=Principal)
def current_user(principal: User):
    return principal


@api.get("/assets", response_model=list[AssetView])
def list_assets(session: Database, principal: User, q: Annotated[str, Query(max_length=128)] = ""):
    query = scoped(select(Asset), Asset.department, principal)
    if q.strip():
        query = query.where(or_(*(column.icontains(q.strip(), autoescape=True) for column in (
            Asset.code, Asset.name, Asset.location,
        ))))
    return list(session.scalars(query.order_by(Asset.code).limit(100)))


@api.get("/assets/qr/{token}", response_model=AssetView)
def lookup_qr(token: UUID, session: Database, principal: User):
    query = scoped(select(Asset), Asset.department, principal)
    asset = session.scalar(query.where(Asset.qr_token == token))
    if asset is None:
        raise HTTPException(404, "자산을 찾을 수 없습니다.")
    return asset


@api.get("/dashboard", response_model=DashboardView)
def dashboard(session: Database, principal: User):
    inventory = scoped(
        select(Item.category, Asset.status, func.count(Asset.id))
        .select_from(Asset)
        .outerjoin(Item, Asset.item_id == Item.id)
        .where(Asset.status != "disposed")
        .group_by(Item.category, Asset.status),
        Asset.department, principal,
    )
    total = active = 0
    categories: dict[str, int] = {}
    for category, status, count in session.execute(inventory):
        total += count
        active += count if status == "in_use" else 0
        if category:
            categories[category] = categories.get(category, 0) + count
    if categories and sum(categories.values()) < total:
        categories["미분류"] = categories.get("미분류", 0) + total - sum(categories.values())
    overview = DashboardView(total_assets=total, active_assets=active, categories=categories)
    if principal.role not in MANAGERS:
        return overview

    local_now = datetime.now(timezone(timedelta(hours=9)))
    week_start = (local_now - timedelta(days=local_now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    overview.weekly_changes = session.scalar(scoped(
        select(func.count(Movement.id)).where(Movement.created_at >= week_start),
        Movement.department, principal,
    ))
    round_id = session.scalar(scoped(
        select(AuditRound.id).where(AuditRound.started_at.is_not(None))
        .order_by(AuditRound.started_at.desc(), AuditRound.id).limit(1),
        AuditRound.department, principal,
    ))
    if round_id:
        observed = session.scalars(select(AuditTarget).where(
            AuditTarget.round_id == round_id, AuditTarget.observed_at.is_not(None),
        ))
        results = [compare_target(target) for target in observed]
        if results:
            overview.audit_checked = len(results)
            overview.audit_matched = results.count("matched")
            overview.audit_issues = results.count("mismatch") + results.count("missing")
    return overview


@api.post("/jobs", response_model=JobView, status_code=202)
def submit_job(request: JobCreate, session: Database, principal: User):
    return create_job(session, principal, request)


@api.get("/jobs/{job_id}", response_model=JobView)
def get_job(job_id: UUID, session: Database, principal: User):
    query = scoped(select(Job), Job.department, principal)
    job = session.scalar(query.where(Job.id == job_id, Job.owner_id == principal.sub))
    if job is None:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    return job


@internal.post("/jobs/claim", response_model=ClaimResponse)
def claim(request: ClaimRequest, session: Database):
    return claim_job(session, request)


@internal.post("/jobs/{job_id}/complete")
def complete(job_id: UUID, request: CompleteRequest, session: Database):
    return {"status": complete_job(session, job_id, request)}


app.include_router(api)
app.include_router(operations_router)
app.include_router(internal)
