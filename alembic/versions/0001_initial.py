"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-29 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("notification_email", sa.String(255), nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), primary_key=True),
    )

    op.create_table(
        "field_definitions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("help_text", sa.Text, nullable=True),
        sa.Column("input_type", sa.String(20), nullable=False),
        sa.Column("enum_values", sa.Text, nullable=True),
        sa.Column("is_required", sa.Boolean, nullable=False, default=False),
        sa.Column("conditional_on_key", sa.String(100), nullable=True),
        sa.Column("conditional_equals", sa.String(100), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, default=0),
    )
    op.create_index("ix_field_definitions_key", "field_definitions", ["key"])

    op.create_table(
        "field_responsibilities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("field_id", sa.Integer, sa.ForeignKey("field_definitions.id"), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.UniqueConstraint("field_id", "role_id"),
    )

    op.create_table(
        "bit_fc_categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
    )

    op.create_table(
        "system_category_definitions",
        sa.Column("code", sa.String(1), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requires_bv_attachment", sa.Boolean, nullable=False, default=False),
        sa.Column("requires_post_approval", sa.Boolean, nullable=False, default=False),
        sa.Column("expedited", sa.Boolean, nullable=False, default=False),
    )

    op.create_table(
        "application_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("requester_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, default="DRAFT"),
        sa.Column("system_category", sa.String(1), nullable=True),
        sa.Column("application_owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "it_application_owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("short_description", sa.String(280), nullable=True),
        sa.Column("installation_location", sa.Text, nullable=True),
        sa.Column("post_approval_due_date", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "request_owner_deputies",
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
    )

    op.create_table(
        "request_bit_fc",
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), primary_key=True),
        sa.Column("bit_fc_id", sa.Integer, sa.ForeignKey("bit_fc_categories.id"), primary_key=True),
    )

    op.create_table(
        "field_values",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("value_text", sa.Text, nullable=True),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("request_id", "field_key"),
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("uploaded_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="IN_PROGRESS"),
        sa.Column("decided_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.UniqueConstraint("request_id", "field_key", "role_id"),
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=True),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("comments.id"), nullable=True),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("edited_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "revisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=False),
        sa.Column("revision_number", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("snapshot_json", sa.Text, nullable=True),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_role_code", sa.String(50), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("payload_json", sa.Text, nullable=True),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("stage", sa.Integer, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=False),
        sa.Column("recipients_json", sa.Text, nullable=False),
    )

    op.create_table(
        "catalog_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("application_requests.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("version", sa.String(100), nullable=True),
        sa.Column("owner_role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="ACTIVE"),
        sa.Column("effective_from", sa.DateTime, nullable=True),
        sa.Column("last_recertified_at", sa.DateTime, nullable=True),
        sa.Column("fields_json", sa.Text, nullable=True),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("would_send_at", sa.DateTime, nullable=False),
    )

    # Enable WAL mode via connection event (handled in database.py)


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("catalog_entries")
    op.drop_table("reminders")
    op.drop_table("audit_logs")
    op.drop_table("revisions")
    op.drop_table("comments")
    op.drop_table("approval_decisions")
    op.drop_table("attachments")
    op.drop_table("field_values")
    op.drop_table("request_bit_fc")
    op.drop_table("request_owner_deputies")
    op.drop_table("application_requests")
    op.drop_table("system_category_definitions")
    op.drop_table("bit_fc_categories")
    op.drop_table("field_responsibilities")
    op.drop_table("field_definitions")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
