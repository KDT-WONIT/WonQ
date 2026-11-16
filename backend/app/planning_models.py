"""Initial storage for planned workflows whose API and columns can evolve."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class AssetRequest(Base):
    __tablename__ = "asset_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), index=True)
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("user_accounts.id"))
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str | None] = mapped_column(Text)
    movement_id: Mapped[UUID | None] = mapped_column(ForeignKey("movements.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PermissionRequest(Base):
    __tablename__ = "permission_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_accounts.id"), index=True)
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("user_accounts.id"))
    role_code: Mapped[str] = mapped_column(String(32))
    scope_department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    status: Mapped[str] = mapped_column(String(24))
    decided_by: Mapped[UUID | None] = mapped_column(ForeignKey("user_accounts.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditFollowup(Base):
    __tablename__ = "audit_followups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    target_id: Mapped[UUID] = mapped_column(ForeignKey("audit_targets.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str | None] = mapped_column(Text)
    movement_id: Mapped[UUID | None] = mapped_column(ForeignKey("movements.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QrIssue(Base):
    __tablename__ = "qr_issues"
    __table_args__ = (CheckConstraint(
        "intake_line_id IS NOT NULL OR asset_id IS NOT NULL OR stock_id IS NOT NULL",
        name="ck_qr_issues_has_target",
    ),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    intake_line_id: Mapped[UUID | None] = mapped_column(ForeignKey("intake_lines.id"))
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"), index=True)
    stock_id: Mapped[UUID | None] = mapped_column(ForeignKey("stock.id"))
    previous_token: Mapped[UUID | None]
    token: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(24))
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("user_accounts.id"))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EquipmentComponent(Base):
    __tablename__ = "equipment_components"
    __table_args__ = (CheckConstraint(
        "(component_asset_id IS NULL) <> (component_item_id IS NULL)",
        name="ck_equipment_components_has_one_component",
    ),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    equipment_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), index=True)
    component_asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"))
    component_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("items.id"))
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), index=True)
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("user_accounts.id"))
    status: Mapped[str] = mapped_column(String(24))
    scheduled_for: Mapped[date | None]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    item_id: Mapped[UUID] = mapped_column(ForeignKey("items.id"), index=True)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("locations.id"))
    target: Mapped[str] = mapped_column(String(32))
    period_start: Mapped[date]
    period_end: Mapped[date]
    status: Mapped[str] = mapped_column(String(24))
    calculation: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(32))
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    audit_round_id: Mapped[UUID | None] = mapped_column(ForeignKey("audit_rounds.id"))


class ReportVersion(Base):
    __tablename__ = "report_versions"
    __table_args__ = (UniqueConstraint("report_id", "version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("reports.id"))
    version: Mapped[int]
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_accounts.id"))
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(24))
    criteria: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
