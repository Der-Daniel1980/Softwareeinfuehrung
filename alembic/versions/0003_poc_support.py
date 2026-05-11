"""POC-Workflow (Proof of Concept)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-07 09:00:00.000000

Schema-Erweiterung für den vereinfachten POC-Workflow:

- application_requests.is_poc            BOOL  DEFAULT 0
- application_requests.promoted_from_poc INT   FK auf application_requests.id
  (gesetzt, sobald ein POC zu einem Standard-Antrag hochgestuft wird)
- field_definitions.included_in_poc      BOOL  DEFAULT 0
  (pro Frage flaggbar: „diese Frage wird auch im POC abgefragt")
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite + Alembic batch-Modus erfordert benannte Constraints, daher die
    # FK explizit mit `name=...` versehen.
    with op.batch_alter_table("application_requests") as batch:
        batch.add_column(
            sa.Column(
                "is_poc",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(
            sa.Column(
                "promoted_from_poc_id",
                sa.Integer(),
                sa.ForeignKey(
                    "application_requests.id",
                    name="fk_application_requests_promoted_from_poc",
                ),
                nullable=True,
            )
        )

    with op.batch_alter_table("field_definitions") as batch:
        batch.add_column(
            sa.Column(
                "included_in_poc",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    # Sinnvolle Defaults: alle Stammdaten- + Produkt-Felder gehören in den POC,
    # weil ein Proof of Concept mindestens Antragsteller, Produkt und Zweck
    # benötigt. Datenschutz, Lizenzen, SLAs etc. werden zunächst NICHT abgefragt.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE field_definitions SET included_in_poc = 1 "
            "WHERE section IN ('STAMMDATEN', 'PRODUKT', 'ANWENDUNG') "
            "OR key IN ('system_category.code', 'projekt.einfuehrungszeitpunkt', "
            "'sonstiges.anmerkungen')"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("field_definitions") as batch:
        batch.drop_column("included_in_poc")

    with op.batch_alter_table("application_requests") as batch:
        batch.drop_column("promoted_from_poc_id")
        batch.drop_column("is_poc")
