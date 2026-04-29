from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BitFcCategory(Base):
    __tablename__ = "bit_fc_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class SystemCategoryDefinition(Base):
    __tablename__ = "system_category_definitions"

    code: Mapped[str] = mapped_column(String(1), primary_key=True)  # A/B/C/D
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requires_bv_attachment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_post_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expedited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CatalogEntry(Base):
    __tablename__ = "catalog_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # FROM_REQUEST | IMPORTED
    request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("application_requests.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_role_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_recertified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON snapshot

    request: Mapped["ApplicationRequest | None"] = relationship("ApplicationRequest", lazy="select")  # noqa: F821
    owner_role: Mapped["Role | None"] = relationship("Role", lazy="selectin")  # noqa: F821
