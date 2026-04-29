from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.database import get_db
from app.models import BitFcCategory, FieldDefinition, SystemCategoryDefinition

router = APIRouter(tags=["fields"])


@router.get("/fields")
def get_fields(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    fields = db.query(FieldDefinition).order_by(FieldDefinition.sort_order).all()
    return [
        {
            "id": f.id,
            "key": f.key,
            "section": f.section,
            "label": f.label,
            "help_text": f.help_text,
            "input_type": f.input_type,
            "enum_values": f.enum_values,
            "is_required": f.is_required,
            "conditional_on_key": f.conditional_on_key,
            "conditional_equals": f.conditional_equals,
            "sort_order": f.sort_order,
        }
        for f in fields
    ]


@router.get("/bit-fc")
def get_bit_fc(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    cats = db.query(BitFcCategory).all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in cats]


@router.get("/system-categories")
def get_system_categories(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    cats = db.query(SystemCategoryDefinition).all()
    return [
        {
            "code": c.code,
            "label": c.label,
            "description": c.description,
            "requires_bv_attachment": c.requires_bv_attachment,
            "requires_post_approval": c.requires_post_approval,
            "expedited": c.expedited,
        }
        for c in cats
    ]
