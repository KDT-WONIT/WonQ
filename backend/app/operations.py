from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import Principal
from .models import Asset
from .operations_models import AuditRound, AuditTarget, Intake, Movement, Notification, Stock

MANAGERS = {"asset_manager", "purchasing"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def scoped(query, column, user: Principal):
    if user.role == "vendor":
        raise HTTPException(403, "내부 업무에 접근할 수 없습니다.")
    return query if user.role == "purchasing" else query.where(column == user.department)


def require_manager(user: Principal) -> None:
    if user.role not in MANAGERS:
        raise HTTPException(403, "담당자 권한이 필요합니다.")


def save(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "중복된 명세서, 시리얼 또는 처리 요청이 있습니다.") from exc


def intake_scope(user: Principal):
    query = select(Intake)
    if user.role == "vendor" and user.vendor_id:
        return query.where(Intake.vendor_id == user.vendor_id)
    require_manager(user)
    return scoped(query, Intake.department, user)


def get_intake(session: Session, user: Principal, request_id: UUID, lock: bool = False) -> Intake:
    query = intake_scope(user).where(Intake.id == request_id)
    intake = session.scalar(query.with_for_update() if lock else query)
    if intake is None:
        raise HTTPException(404, "납품 요청을 찾을 수 없습니다.")
    return intake


def require_status(current: str, expected: str) -> None:
    if current != expected:
        raise HTTPException(409, "현재 상태에서는 처리할 수 없습니다.")


def notify(session: Session, audience: str, recipient: str, title: str, reference_id: UUID) -> None:
    session.add(Notification(audience=audience, recipient=recipient, title=title, reference_id=reference_id))


def add_movement(session: Session, *, key: str, department: str, kind: str,
                 target: UUID, user: Principal, details: dict) -> None:
    session.add(Movement(
        stable_key=key, department=department, kind=kind, target=str(target), actor=user.sub, details=details,
    ))


def receive_stock(session: Session, intake: Intake, line) -> UUID:
    values = {
        "id": uuid4(), "department": intake.department, "item_code": line.item_code,
        "name": line.name, "location": line.location, "quantity": line.accepted_quantity,
        "safety_stock": 0,
        "item_id": line.item_id, "department_id": intake.department_id, "location_id": line.location_id,
    }
    query = insert(Stock).values(**values).on_conflict_do_update(
        index_elements=["department", "item_code", "location"],
        set_={
            "quantity": Stock.quantity + line.accepted_quantity,
            "item_id": func.coalesce(Stock.item_id, line.item_id),
            "department_id": func.coalesce(Stock.department_id, intake.department_id),
            "location_id": func.coalesce(Stock.location_id, line.location_id),
        },
    ).returning(Stock.id)
    return session.scalar(query)


def get_round(session: Session, user: Principal, round_id: UUID, lock: bool = False) -> AuditRound:
    require_manager(user)
    query = scoped(select(AuditRound), AuditRound.department, user).where(AuditRound.id == round_id)
    item = session.scalar(query.with_for_update() if lock else query)
    if item is None:
        raise HTTPException(404, "실사 회차를 찾을 수 없습니다.")
    return item


def require_assignee(round_: AuditRound, user: Principal) -> None:
    if round_.assigned_to != user.sub:
        raise HTTPException(403, "배정된 담당자가 실사를 진행해야 합니다.")


def compare_target(target: AuditTarget) -> str:
    if target.observed_quantity is None:
        return "unchecked"
    if target.observed_quantity == 0 and target.expected_quantity > 0:
        return "missing"
    if target.observed_quantity != target.expected_quantity or (
        target.observed_quantity > 0 and target.observed_location != target.expected_location
    ):
        return "mismatch"
    return "matched"


def audit_view(item: AuditRound) -> dict:
    return {
        "id": item.id, "title": item.title, "department": item.department,
        "status": item.status, "location": item.location, "assigned_to": item.assigned_to,
        "scheduled_for": item.scheduled_for, "started_at": item.started_at,
        "finished_at": item.finished_at, "approved_at": item.approved_at,
        "targets": [
            {
                "id": target.id, "kind": target.kind, "label": target.label,
                "expected_location": target.expected_location, "expected_quantity": target.expected_quantity,
                "observed_location": target.observed_location, "observed_quantity": target.observed_quantity,
                "result": compare_target(target),
            }
            for target in item.targets
        ],
    }
