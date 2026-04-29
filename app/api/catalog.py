from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user, require_admin
from app.core.csrf import verify_api_csrf
from app.database import get_db
from app.models import CatalogEntry
from app.models.enums import CatalogSource
from app.schemas.catalog import CatalogImport, CatalogRead
from app.services.catalog import export_csv

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=list[CatalogRead])
def list_catalog(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[CatalogRead]:
    entries = db.query(CatalogEntry).all()
    return [_to_read(e) for e in entries]


@router.get("/export.csv", response_class=PlainTextResponse)
def export_catalog_csv(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> str:
    return export_csv(db)


@router.get("/{entry_id}", response_model=CatalogRead)
def get_catalog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> CatalogRead:
    entry = db.get(CatalogEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _to_read(entry)


@router.post("/import", response_model=CatalogRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(verify_api_csrf)])
def import_catalog(
    body: CatalogImport,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> CatalogRead:
    from datetime import datetime

    entry = CatalogEntry(
        source=CatalogSource.IMPORTED.value,
        name=body.name,
        vendor=body.vendor,
        version=body.version,
        status="ACTIVE",
        effective_from=datetime.utcnow(),
        fields_json=body.fields_json,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_read(entry)


def _to_read(e: CatalogEntry) -> CatalogRead:
    return CatalogRead(
        id=e.id,
        source=e.source,
        request_id=e.request_id,
        name=e.name,
        vendor=e.vendor,
        version=e.version,
        status=e.status,
        effective_from=e.effective_from,
        last_recertified_at=e.last_recertified_at,
        fields_json=e.fields_json,
    )
