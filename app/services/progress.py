"""Compute per-role review progress for an ApplicationRequest.

Used by the requests list, review panel and dashboard so the requester
and reviewers all see the same numbers ("BR 2/4 offen") at a glance.
The function intentionally returns plain dicts so it can be passed
straight into Jinja templates without ORM lifecycle concerns.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    ApplicationRequest,
    ApprovalDecision,
    FieldDefinition,
    FieldResponsibility,
    Role,
)
from app.models.enums import Responsibility


def role_progress(session: Session, req: ApplicationRequest) -> list[dict]:
    """Return one entry per reviewer-role with progress counters.

    Order is stable (alphabetical by role code) so the UI is predictable.
    Each entry::

        {
            "role_code": "BETRIEBSRAT",
            "role_label": "Betriebsrat",
            "total": 4,            # fields where this role has APPROVAL
            "approved": 1,
            "rejected": 1,
            "in_review": 0,
            "open": 2,             # no decision row yet
            "done": 2,             # approved + rejected (final)
            "open_questions": 1,   # rejected + in_review w/ comment
        }
    """
    # All approval-responsibilities once
    rows = (
        session.query(
            FieldResponsibility.role_id,
            Role.code,
            Role.label,
            FieldDefinition.key,
            FieldDefinition.label,
        )
        .join(Role, Role.id == FieldResponsibility.role_id)
        .join(FieldDefinition, FieldDefinition.id == FieldResponsibility.field_id)
        .filter(FieldResponsibility.kind == Responsibility.APPROVAL.value)
        .all()
    )

    # Existing decisions for this request, keyed by (field_key, role_id)
    decisions = {
        (d.field_key, d.role_id): d
        for d in session.query(ApprovalDecision)
        .filter(ApprovalDecision.request_id == req.id)
        .all()
    }

    by_role: dict[str, dict] = {}
    for role_id, code, role_label, field_key, field_label in rows:
        slot = by_role.setdefault(
            code,
            {
                "role_code": code,
                "role_label": role_label or code,
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "in_review": 0,
                "open": 0,
                "done": 0,
                "open_questions": 0,
                "questions": [],  # list of {field_key, field_label, status, comment}
            },
        )
        slot["total"] += 1
        d = decisions.get((field_key, role_id))
        if d is None:
            slot["open"] += 1
        elif d.status == "APPROVED":
            slot["approved"] += 1
            slot["done"] += 1
        elif d.status == "REJECTED":
            slot["rejected"] += 1
            slot["done"] += 1
            if d.comment:
                slot["open_questions"] += 1
                slot["questions"].append(
                    {
                        "field_key": field_key,
                        "field_label": field_label or field_key,
                        "status": "REJECTED",
                        "comment": d.comment,
                    }
                )
        elif d.status == "IN_REVIEW":
            slot["in_review"] += 1
            if d.comment:
                slot["open_questions"] += 1
                slot["questions"].append(
                    {
                        "field_key": field_key,
                        "field_label": field_label or field_key,
                        "status": "IN_REVIEW",
                        "comment": d.comment,
                    }
                )
        else:
            slot["open"] += 1

    return sorted(by_role.values(), key=lambda r: r["role_code"])


def overall_summary(progress: list[dict]) -> dict:
    """Top-level counters across all roles, useful for the dashboard."""
    total = sum(r["total"] for r in progress)
    done = sum(r["done"] for r in progress)
    rejected = sum(r["rejected"] for r in progress)
    open_q = sum(r["open_questions"] for r in progress)
    return {
        "total": total,
        "done": done,
        "open": total - done,
        "rejected": rejected,
        "open_questions": open_q,
        "percent": round(100 * done / total) if total else 0,
    }
