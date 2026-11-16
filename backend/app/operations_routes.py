from io import BytesIO
from typing import Annotated
from uuid import UUID, uuid4

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from .auth import Principal, get_principal
from .db import get_session
from .models import Asset
from .operations import (
    MANAGERS, add_movement, audit_view, get_intake, get_round, intake_scope, now, notify,
    receive_stock, require_assignee, require_manager, require_status, save, scoped,
)
from .operations_models import AuditRound, AuditTarget, Intake, IntakeLine, Movement, Notification, NotificationRead, Stock
from .reference_models import Department, Item, Vendor
from .operations_schemas import (
    AuditCreate, AuditObservation, IntakeCreate, IntakeReview, IntakeView, InspectionReceipt, SignReceipt,
    StockThreshold, StockUse,
)

router = APIRouter(prefix="/api", tags=["업무"])
Database = Annotated[Session, Depends(get_session)]
User = Annotated[Principal, Depends(get_principal)]


@router.get("/intakes", response_model=list[IntakeView])
def list_intakes(session: Database, user: User):
    return session.scalars(intake_scope(user).options(selectinload(Intake.lines)).order_by(Intake.created_at.desc()).limit(100)).all()


@router.post("/intakes", response_model=IntakeView, status_code=201)
def submit_intake(data: IntakeCreate, session: Database, user: User):
    if user.role != "vendor" or not user.vendor_id:
        raise HTTPException(403, "납품업체 계정이 필요합니다.")
    item = Intake(
        id=uuid4(), vendor_id=user.vendor_id, owner_id=user.sub, document_number=data.document_number, department=data.department,
        supplier_id=session.scalar(select(Vendor.id).where(Vendor.code == user.vendor_id)),
        department_id=session.scalar(select(Department.id).where(Department.code == data.department)),
        lines=[
            IntakeLine(position=index, item_code=line.item_code, name=line.name, tracking=line.tracking,
                       submitted_quantity=line.quantity, location=line.location)
            for index, line in enumerate(data.lines)
        ],
    )
    session.add(item)
    notify(session, "department", item.department, "납품 등록 검토 요청", item.id)
    save(session)
    return item


@router.post("/intakes/{request_id}/review", response_model=IntakeView)
def review_intake(request_id: UUID, data: IntakeReview, session: Database, user: User):
    require_manager(user)
    item = get_intake(session, user, request_id, lock=True)
    require_status(item.status, "submitted")
    if data.decision == "reject" and not data.note:
        raise HTTPException(422, "반려 사유를 입력하세요.")
    if data.decision == "approve":
        if not data.quantities.keys() <= {line.id for line in item.lines}:
            raise HTTPException(422, "요청에 없는 품목입니다.")
        catalog = {entry.code: entry for entry in session.scalars(
            select(Item).where(Item.code.in_([line.item_code for line in item.lines]))
        )}
        for line in item.lines:
            quantity = data.quantities.get(line.id, line.submitted_quantity)
            if not 0 < quantity <= line.submitted_quantity:
                raise HTTPException(422, "승인 수량은 제출 수량 이내여야 합니다.")
            line.approved_quantity = quantity
            entry = catalog.get(line.item_code)
            if entry and (entry.tracking is None or entry.tracking == line.tracking):
                line.item_id = entry.id
            line.labels = [str(uuid4()) for _ in range(quantity)] if line.tracking == "individual" else []
    item.status = "approved" if data.decision == "approve" else "rejected"
    item.review_note, item.reviewed_by, item.reviewed_at = data.note, user.sub, now()
    notify(session, "user", item.owner_id, "납품 등록 승인" if item.status == "approved" else "납품 등록 반려", item.id)
    save(session)
    return item


@router.post("/intakes/{request_id}/inspect", response_model=IntakeView)
def inspect_intake(request_id: UUID, data: InspectionReceipt, session: Database, user: User):
    require_manager(user)
    item = get_intake(session, user, request_id, lock=True)
    if item.status not in {"approved", "inspected"}:
        raise HTTPException(409, "승인된 요청만 검수할 수 있습니다.")
    by_id = {line.line_id: line for line in data.lines}
    if len(by_id) != len(data.lines) or set(by_id) != {line.id for line in item.lines}:
        raise HTTPException(422, "모든 승인 품목을 한 번씩 입력하세요.")
    if not any(line.accepted for line in data.lines):
        raise HTTPException(422, "입고할 검수 합격 수량이 필요합니다.")
    seen_serials = set()
    for line in item.lines:
        receipt = by_id[line.id]
        if receipt.accepted > min(receipt.received, line.approved_quantity):
            raise HTTPException(422, "합격 수량은 승인·수령 수량 이내여야 합니다.")
        if (receipt.received != line.approved_quantity or receipt.accepted != receipt.received) and not receipt.note:
            raise HTTPException(422, "수량 차이 사유를 입력하세요.")
        if receipt.serials and (line.tracking != "individual" or len(receipt.serials) != receipt.accepted):
            raise HTTPException(422, "시리얼을 입력할 때는 합격한 개별 자산마다 입력하세요.")
        for serial in receipt.serials:
            key = (line.item_code, serial)
            if key in seen_serials or session.scalar(
                select(Asset.id).where(Asset.item_code == line.item_code, Asset.serial == serial)
            ):
                raise HTTPException(409, "이미 등록되었거나 중복 입력된 시리얼입니다.")
            seen_serials.add(key)
        line.received_quantity, line.accepted_quantity = receipt.received, receipt.accepted
        line.serials, line.variance_note = receipt.serials, receipt.note
    item.status = "inspected"
    save(session)
    return item


@router.post("/intakes/{request_id}/sign", response_model=IntakeView)
def sign_intake(request_id: UUID, data: SignReceipt, session: Database, user: User):
    if user.role != "vendor":
        raise HTTPException(403, "납품업체 계정이 필요합니다.")
    item = get_intake(session, user, request_id, lock=True)
    require_status(item.status, "inspected")
    item.status, item.signer_name, item.signed_by, item.signed_at = "signed", data.name, user.sub, now()
    notify(session, "department", item.department, "입고 확인서 서명 완료", item.id)
    save(session)
    return item


@router.post("/intakes/{request_id}/receive", response_model=IntakeView)
def finalize_intake(request_id: UUID, session: Database, user: User):
    require_manager(user)
    item = get_intake(session, user, request_id, lock=True)
    if item.status == "received":
        return item
    require_status(item.status, "signed")
    for line in item.lines:
        quantity = line.accepted_quantity
        if not quantity:
            continue
        if line.tracking == "quantity":
            stock_id = receive_stock(session, item, line)
            add_movement(session, key=f"receipt:{line.id}", department=item.department,
                         kind="receipt", target=stock_id, user=user, details={"quantity": quantity, "intake_id": str(item.id)})
            continue
        for index, raw_token in enumerate(line.labels[:quantity]):
            token = UUID(raw_token)
            asset = Asset(
                id=uuid4(), code=f"AST-{token.hex.upper()}", name=line.name, department=item.department,
                location=line.location, qr_token=token, item_code=line.item_code,
                item_id=line.item_id, department_id=item.department_id, location_id=line.location_id,
                intake_line_id=line.id,
                serial=line.serials[index] if line.serials else None,
            )
            session.add(asset)
            add_movement(session, key=f"receipt:{token}", department=item.department, kind="receipt",
                         target=asset.id, user=user, details={"quantity": 1, "intake_id": str(item.id)})
    item.status, item.received_by, item.received_at = "received", user.sub, now()
    notify(session, "user", item.owner_id, "입고 확정 완료", item.id)
    save(session)
    return item


@router.get("/intakes/{request_id}/labels/{token}")
def print_label(request_id: UUID, token: UUID, session: Database, user: User):
    item = get_intake(session, user, request_id)
    if not any(str(token) in line.labels[:line.accepted_quantity if item.status == "received" else None]
               for line in item.lines):
        raise HTTPException(404, "발급된 QR을 찾을 수 없습니다.")
    image = BytesIO()
    qrcode.make(str(token), box_size=5).save(image, format="PNG")
    return Response(image.getvalue(), media_type="image/png", headers={"Cache-Control": "private, no-store"})


@router.get("/stock")
def list_stock(session: Database, user: User):
    require_manager(user)
    return session.scalars(scoped(select(Stock), Stock.department, user).order_by(Stock.item_code).limit(100)).all()


@router.post("/stock/{stock_id}/use")
def use_stock(stock_id: UUID, data: StockUse, session: Database, user: User):
    require_manager(user)
    stock = session.scalar(scoped(select(Stock), Stock.department, user).where(Stock.id == stock_id).with_for_update())
    if stock is None:
        raise HTTPException(404, "재고를 찾을 수 없습니다.")
    key = f"stock:{data.operation_id}"
    existing = session.scalar(select(Movement).where(Movement.stable_key == key))
    if existing:
        if existing.target != str(stock.id) or existing.actor != user.sub or existing.kind != data.purpose or (
            existing.details["quantity"], existing.details["note"]
        ) != (data.quantity, data.note):
            raise HTTPException(409, "같은 작업 ID에 다른 요청이 이미 존재합니다.")
        return stock
    if stock.quantity < data.quantity:
        raise HTTPException(409, "현재고가 부족합니다.")
    before = stock.quantity
    stock.quantity -= data.quantity
    add_movement(session, key=key, department=stock.department, kind=data.purpose, target=stock.id,
                 user=user, details={"quantity": data.quantity, "note": data.note, "before": before, "after": stock.quantity})
    if before >= stock.safety_stock > stock.quantity:
        notify(session, "role", "purchasing", f"안전재고 미달 · {stock.name}", stock.id)
    save(session)
    return stock


@router.post("/stock/{stock_id}/threshold")
def set_stock_threshold(stock_id: UUID, data: StockThreshold, session: Database, user: User):
    require_manager(user)
    query = scoped(select(Stock), Stock.department, user).where(Stock.id == stock_id).with_for_update()
    stock = session.scalar(query)
    if stock is None:
        raise HTTPException(404, "재고를 찾을 수 없습니다.")
    if stock.safety_stock <= stock.quantity < data.quantity:
        notify(session, "role", "purchasing", f"안전재고 미달 · {stock.name}", stock.id)
    stock.safety_stock = data.quantity
    save(session)
    return stock


@router.get("/movements")
def list_movements(session: Database, user: User):
    require_manager(user)
    return session.scalars(scoped(select(Movement), Movement.department, user).order_by(Movement.created_at.desc()).limit(100)).all()


@router.get("/audits")
def list_audits(session: Database, user: User):
    require_manager(user)
    query = scoped(select(AuditRound), AuditRound.department, user).options(selectinload(AuditRound.targets))
    return [audit_view(item) for item in session.scalars(query.order_by(AuditRound.id).limit(50))]


@router.post("/audits", status_code=201)
def create_audit(data: AuditCreate, session: Database, user: User):
    require_manager(user)
    if data.assigned_to and data.assigned_to != user.sub and user.role != "purchasing":
        raise HTTPException(403, "다른 담당자에게 배정하려면 구매 담당자 권한이 필요합니다.")
    item = AuditRound(id=uuid4(), department=user.department, title=data.title, location=data.location,
                      department_id=session.scalar(select(Department.id).where(Department.code == user.department)),
                      assigned_to=data.assigned_to or user.sub, scheduled_for=data.scheduled_for)
    session.add(item)
    notify(session, "user", item.assigned_to, "실사 일정 배정", item.id)
    save(session)
    return audit_view(item)


@router.post("/audits/{round_id}/start")
def start_audit(round_id: UUID, session: Database, user: User):
    item = get_round(session, user, round_id, lock=True)
    require_assignee(item, user)
    require_status(item.status, "scheduled")
    assets = select(
        Asset.id, literal("individual"), Asset.name, Asset.code, Asset.location, literal(1),
    ).where(Asset.department == item.department, Asset.status != "disposed")
    stock = select(
        Stock.id, literal("quantity"), Stock.name, Stock.item_code, Stock.location, Stock.quantity,
    ).where(Stock.department == item.department)
    if item.location:
        assets = assets.where(Asset.location == item.location)
        stock = stock.where(Stock.location == item.location)
    targets = [
        AuditTarget(target_id=target_id, kind=kind, label=f"{name} · {code}",
                    expected_location=location, expected_quantity=quantity)
        for target_id, kind, name, code, location, quantity in session.execute(union_all(assets, stock))
    ]
    if not targets:
        raise HTTPException(409, "선택한 범위에 실사 대상이 없습니다.")
    item.targets = targets
    item.status, item.started_at = "running", now()
    save(session)
    return audit_view(item)


@router.post("/audits/{round_id}/observe")
def observe_audit(round_id: UUID, data: AuditObservation, session: Database, user: User):
    item = get_round(session, user, round_id, lock=True)
    require_assignee(item, user)
    require_status(item.status, "running")
    if data.qr_token:
        asset_id = session.scalar(select(Asset.id).where(Asset.qr_token == data.qr_token, Asset.department == item.department))
        target = next((row for row in item.targets if row.kind == "individual" and row.target_id == asset_id), None)
    else:
        target = next((row for row in item.targets if row.id == data.target_id), None)
    if target is None:
        raise HTTPException(404, "이 회차의 실사 대상이 아닙니다.")
    if target.kind == "individual" and data.quantity > 1:
        raise HTTPException(422, "개별 자산은 0 또는 1로 기록하세요.")
    if target.observed_at:
        if (target.observed_quantity, target.observed_location) == (data.quantity, data.location):
            return audit_view(item)
        raise HTTPException(409, "최초 확인값이 저장되었습니다. 변경은 후속 조치로 기록해야 합니다.")
    target.observed_quantity, target.observed_location = data.quantity, data.location
    target.observed_by, target.observed_at = user.sub, now()
    save(session)
    return audit_view(item)


@router.post("/audits/{round_id}/finish")
def finish_audit(round_id: UUID, session: Database, user: User):
    item = get_round(session, user, round_id, lock=True)
    require_assignee(item, user)
    require_status(item.status, "running")
    item.status, item.finished_at = "review", now()
    notify(session, "role", "purchasing", "실사 결과 검토 요청", item.id)
    save(session)
    return audit_view(item)


@router.post("/audits/{round_id}/approve")
def approve_audit(round_id: UUID, session: Database, user: User):
    if user.role != "purchasing":
        raise HTTPException(403, "구매 담당자 권한이 필요합니다.")
    item = get_round(session, user, round_id, lock=True)
    require_status(item.status, "review")
    item.status, item.approved_at, item.approved_by = "completed", now(), user.sub
    notify(session, "user", item.assigned_to, "실사 결과 승인", item.id)
    save(session)
    return audit_view(item)


def notification_scope(user: User):
    filters = [and_(Notification.audience == "user", Notification.recipient == user.sub)]
    if user.role in MANAGERS:
        department = Notification.audience == "department"
        if user.role != "purchasing":
            department = and_(department, Notification.recipient == user.department)
        filters.extend([department, and_(Notification.audience == "role", Notification.recipient == user.role)])
    return or_(*filters)


@router.get("/notifications")
def list_notifications(session: Database, user: User):
    scope = notification_scope(user)
    query = select(Notification, NotificationRead.read_at).outerjoin(
        NotificationRead,
        and_(NotificationRead.notification_id == Notification.id, NotificationRead.user_id == user.sub),
    ).where(scope)
    unread = session.scalar(
        select(func.count()).select_from(query.where(NotificationRead.read_at.is_(None)).subquery())
    )
    return {"unread": unread, "items": [
        {"id": item.id, "title": item.title, "reference_id": item.reference_id,
         "created_at": item.created_at, "read_at": read_at}
        for item, read_at in session.execute(query.order_by(Notification.created_at.desc()).limit(100))
    ]}


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_notification(notification_id: UUID, session: Database, user: User):
    if session.scalar(select(Notification.id).where(Notification.id == notification_id, notification_scope(user))) is None:
        raise HTTPException(404, "알림을 찾을 수 없습니다.")
    session.execute(insert(NotificationRead).values(notification_id=notification_id, user_id=user.sub).on_conflict_do_nothing())
    save(session)
