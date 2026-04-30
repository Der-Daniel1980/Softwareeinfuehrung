"""vendors table + BIT/FC re-categorisation

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30 09:00:00.000000

- Adds the `vendors` table for Hersteller master-data with admin CRUD.
- Wipes obsolete BIT/FC categories (the seed re-creates the new amedes set).
  Existing request_bit_fc associations to obsolete entries are deleted.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Names that survive the migration. Anything NOT in this set is dropped from
# bit_fc_categories (cascading via request_bit_fc cleanup).
NEW_BIT_FC_NAMES = (
    "BIT Enterprise",
    "BIT Lab",
    "Digital Security",
    "BIT CLM & Genetics",
    "IT Operations",
    "Digital Processes",
    "BIT Enterprise Data & Intelligence",
)


def upgrade() -> None:
    # 1. New vendors table
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_vendors_name", "vendors", ["name"])

    # 2. Drop obsolete BIT/FC associations + categories
    bind = op.get_bind()
    placeholders = ", ".join(f":n{i}" for i, _ in enumerate(NEW_BIT_FC_NAMES))
    params = {f"n{i}": v for i, v in enumerate(NEW_BIT_FC_NAMES)}

    # Find ids of obsolete categories
    obsolete = bind.execute(
        sa.text(
            f"SELECT id FROM bit_fc_categories WHERE name NOT IN ({placeholders})"
        ),
        params,
    ).fetchall()
    obsolete_ids = [row[0] for row in obsolete]

    if obsolete_ids:
        ph = ", ".join(f":i{i}" for i, _ in enumerate(obsolete_ids))
        id_params = {f"i{i}": v for i, v in enumerate(obsolete_ids)}
        bind.execute(
            sa.text(f"DELETE FROM request_bit_fc WHERE bit_fc_id IN ({ph})"),
            id_params,
        )
        bind.execute(
            sa.text(f"DELETE FROM bit_fc_categories WHERE id IN ({ph})"),
            id_params,
        )


def downgrade() -> None:
    op.drop_index("ix_vendors_name", table_name="vendors")
    op.drop_table("vendors")
    # Note: obsolete BIT/FC entries are not restored.
