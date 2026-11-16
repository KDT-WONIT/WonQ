from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("item_code", "serial", name="uq_assets_item_serial"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    department: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(128))
    qr_token: Mapped[UUID] = mapped_column(default=uuid4, unique=True)
    item_code: Mapped[str | None] = mapped_column(String(64))
    serial: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), server_default="stored")
    item_id: Mapped[UUID | None] = mapped_column(ForeignKey("items.id"), index=True)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"))
    holder_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_accounts.id"))
    intake_line_id: Mapped[UUID | None] = mapped_column(ForeignKey("intake_lines.id"))


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_claim", "kind", "status", "created_at"),
        Index("ix_jobs_publish", "status", "published_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(24))
    owner_id: Mapped[str] = mapped_column(String(128))
    department: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attempts: Mapped[int] = mapped_column(default=0)
    lease_token: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
