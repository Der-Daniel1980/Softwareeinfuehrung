from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user, require_admin
from app.core.csrf import verify_api_csrf
from app.database import get_db
from app.models import Vendor
from app.models.enums import AuditAction
from app.schemas.vendor import VendorCreate, VendorRead, VendorUpdate
from app.services import audit

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorRead])
def list_vendors(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
    include_inactive: bool = False,
) -> list[VendorRead]:
    q = db.query(Vendor)
    if not include_inactive:
        q = q.filter(Vendor.is_active.is_(True))
    return [VendorRead.model_validate(v) for v in q.order_by(Vendor.name).all()]


@router.post(
    "",
    response_model=VendorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_csrf)],
)
def create_vendor(
    body: VendorCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> VendorRead:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    existing = db.query(Vendor).filter(Vendor.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hersteller '{name}' existiert bereits",
        )
    v = Vendor(
        name=name,
        description=body.description,
        website=body.website,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(v)
    audit.log(db, admin, AuditAction.USER_CREATED.value, "Vendor", name)
    db.commit()
    db.refresh(v)
    return VendorRead.model_validate(v)


@router.patch(
    "/{vendor_id}",
    response_model=VendorRead,
    dependencies=[Depends(verify_api_csrf)],
)
def update_vendor(
    vendor_id: int,
    body: VendorUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> VendorRead:
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, val in data.items():
        setattr(v, k, val)
    audit.log(db, admin, AuditAction.USER_CREATED.value, "Vendor", v.name, payload=data)
    db.commit()
    db.refresh(v)
    return VendorRead.model_validate(v)


@router.delete(
    "/{vendor_id}",
    dependencies=[Depends(verify_api_csrf)],
)
def deactivate_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    """Soft-delete: sets is_active=False to preserve referential history."""
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    v.is_active = False
    audit.log(db, admin, AuditAction.USER_CREATED.value, "Vendor", v.name,
              payload={"action": "deactivated"})
    db.commit()
    return {"ok": True}
