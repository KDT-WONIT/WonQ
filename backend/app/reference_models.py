from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), index=True)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    default_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"))


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str | None] = mapped_column(String(128))
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("departments.id"))
    vendor_id: Mapped[UUID | None] = mapped_column(ForeignKey("vendors.id"))


class Item(Base):
    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(80))
    tracking: Mapped[str | None] = mapped_column(String(16))
    base_unit: Mapped[str | None] = mapped_column(String(32))
    attributes: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("user_accounts.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
