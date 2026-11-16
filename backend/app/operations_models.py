from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Intake(Base):
    __tablename__ = "intakes"
    __table_args__ = (UniqueConstraint("vendor_id", "document_number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vendor_id: Mapped[str] = mapped_column(String(64))
    owner_id: Mapped[str] = mapped_column(String(128))
    document_number: Mapped[str] = mapped_column(String(80))
    department: Mapped[str] = mapped_column(String(64), index=True)
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("vendors.id"))
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    review_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_by: Mapped[str | None] = mapped_column(String(128))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_by: Mapped[str | None] = mapped_column(String(128))
    signer_name: Mapped[str | None] = mapped_column(String(80))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by: Mapped[str | None] = mapped_column(String(128))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lines: Mapped[list["IntakeLine"]] = relationship(order_by="IntakeLine.position", cascade="all, delete-orphan")


class IntakeLine(Base):
    __tablename__ = "intake_lines"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    intake_id: Mapped[UUID] = mapped_column(ForeignKey("intakes.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    item_code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    tracking: Mapped[str] = mapped_column(String(16))
    item_id: Mapped[UUID | None] = mapped_column(ForeignKey("items.id"))
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"))
    submitted_quantity: Mapped[int]
    approved_quantity: Mapped[int | None]
    location: Mapped[str] = mapped_column(String(128))
    labels: Mapped[list] = mapped_column(JSON, default=list)
    received_quantity: Mapped[int | None]
    accepted_quantity: Mapped[int | None]
    serials: Mapped[list] = mapped_column(JSON, default=list)
    variance_note: Mapped[str | None] = mapped_column(String(500))


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("department", "item_code", "location"),
        CheckConstraint("quantity >= 0", name="ck_stock_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    department: Mapped[str] = mapped_column(String(64), index=True)
    item_code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    item_id: Mapped[UUID | None] = mapped_column(ForeignKey("items.id"))
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"))
    location: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int]
    safety_stock: Mapped[int] = mapped_column(default=0)


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stable_key: Mapped[str] = mapped_column(String(120), unique=True)
    department: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(String(128))
    actor: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditRound(Base):
    __tablename__ = "audit_rounds"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    department: Mapped[str] = mapped_column(String(64), index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"))
    title: Mapped[str] = mapped_column(String(128))
    assigned_to: Mapped[str] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(128))
    targets: Mapped[list["AuditTarget"]] = relationship(cascade="all, delete-orphan", order_by="AuditTarget.label")


class AuditTarget(Base):
    __tablename__ = "audit_targets"
    __table_args__ = (UniqueConstraint("round_id", "target_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    round_id: Mapped[UUID] = mapped_column(ForeignKey("audit_rounds.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(200))
    expected_location: Mapped[str] = mapped_column(String(128))
    expected_quantity: Mapped[int]
    observed_location: Mapped[str | None] = mapped_column(String(128))
    observed_quantity: Mapped[int | None]
    observed_by: Mapped[str | None] = mapped_column(String(128))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    audience: Mapped[str] = mapped_column(String(20))
    recipient: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(200))
    reference_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    notification_id: Mapped[UUID] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
