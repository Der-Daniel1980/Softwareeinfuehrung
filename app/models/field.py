from __future__ import annotations

from typing import List

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FieldDefinition(Base):
    __tablename__ = "field_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_type: Mapped[str] = mapped_column(String(20), nullable=False)
    enum_values: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conditional_on_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    conditional_equals: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    responsibilities: Mapped[List["FieldResponsibility"]] = relationship(
        "FieldResponsibility", back_populates="field", lazy="selectin"
    )


class FieldResponsibility(Base):
    __tablename__ = "field_responsibilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_id: Mapped[int] = mapped_column(Integer, ForeignKey("field_definitions.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # INFO | APPROVAL

    field: Mapped["FieldDefinition"] = relationship("FieldDefinition", back_populates="responsibilities")
    role: Mapped["Role"] = relationship("Role", lazy="selectin")  # noqa: F821
