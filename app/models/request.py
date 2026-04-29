from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RequestStatus

# Association: request <-> bit_fc_categories
request_bit_fc = Table(
    "request_bit_fc",
    Base.metadata,
    Column("request_id", Integer, ForeignKey("application_requests.id"), primary_key=True),
    Column("bit_fc_id", Integer, ForeignKey("bit_fc_categories.id"), primary_key=True),
)

# Association: request owner deputies
request_owner_deputies = Table(
    "request_owner_deputies",
    Base.metadata,
    Column("request_id", Integer, ForeignKey("application_requests.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("kind", String(20), nullable=False),  # FACHLICH | TECHNISCH
)


class ApplicationRequest(Base):
    __tablename__ = "application_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=RequestStatus.DRAFT.value, nullable=False
    )
    system_category: Mapped[str | None] = mapped_column(String(1), nullable=True)
    application_owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    it_application_owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    short_description: Mapped[str | None] = mapped_column(String(280), nullable=True)
    installation_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_approval_due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id], lazy="selectin")  # noqa: F821
    application_owner: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[application_owner_id], lazy="selectin"
    )
    it_application_owner: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[it_application_owner_id], lazy="selectin"
    )
    bit_fc_categories: Mapped[List["BitFcCategory"]] = relationship(  # noqa: F821
        "BitFcCategory", secondary=request_bit_fc, lazy="selectin"
    )
    field_values: Mapped[List["FieldValue"]] = relationship(
        "FieldValue", back_populates="request", lazy="selectin"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment", back_populates="request", lazy="selectin"
    )
    decisions: Mapped[List["ApprovalDecision"]] = relationship(
        "ApprovalDecision", back_populates="request", lazy="selectin"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="request", lazy="select"
    )


class FieldValue(Base):
    __tablename__ = "field_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_requests.id"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    request: Mapped["ApplicationRequest"] = relationship(
        "ApplicationRequest", back_populates="field_values"
    )
    updater: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by], lazy="selectin")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("request_id", "field_key"),
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_requests.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    request: Mapped["ApplicationRequest"] = relationship(
        "ApplicationRequest", back_populates="attachments"
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_requests.id"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS", nullable=False)
    decided_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped["ApplicationRequest"] = relationship(
        "ApplicationRequest", back_populates="decisions"
    )
    role: Mapped["Role"] = relationship("Role", lazy="selectin")  # noqa: F821
    decider: Mapped["User | None"] = relationship("User", foreign_keys=[decided_by], lazy="selectin")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("request_id", "field_key", "role_id"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("application_requests.id"), nullable=False
    )
    field_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("roles.id"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("comments.id"), nullable=True
    )
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    request: Mapped["ApplicationRequest"] = relationship(
        "ApplicationRequest", back_populates="comments"
    )
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], lazy="selectin")  # noqa: F821
    role: Mapped["Role | None"] = relationship("Role", lazy="selectin")  # noqa: F821
    replies: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="parent", lazy="select"
    )
    parent: Mapped["Comment | None"] = relationship(
        "Comment", back_populates="replies", remote_side="Comment.id"
    )
