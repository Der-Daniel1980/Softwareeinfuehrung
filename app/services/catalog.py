from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ApplicationRequest, CatalogEntry
from app.models.enums import CatalogSource


def promote(session: Session, req: ApplicationRequest) -> CatalogEntry:
    """Idempotently create a CatalogEntry from an APPROVED request."""
    existing = (
        session.query(CatalogEntry).filter(CatalogEntry.request_id == req.id).first()
    )
    if existing:
        return existing

    # Gather relevant fields for the snapshot
    fv_map = {fv.field_key: fv.value_text for fv in req.field_values}
    name = fv_map.get("produkt.name") or req.title
    vendor = fv_map.get("produkt.hersteller")
    version = fv_map.get("produkt.version")

    entry = CatalogEntry(
        source=CatalogSource.FROM_REQUEST.value,
        request_id=req.id,
        name=name,
        vendor=vendor,
        version=version,
        status="ACTIVE",
        effective_from=datetime.utcnow(),
        fields_json=json.dumps(fv_map),
    )
    session.add(entry)
    return entry


def export_csv(session: Session) -> str:
    """Return CSV body string of all catalog entries."""
    entries = session.query(CatalogEntry).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "source", "request_id", "name", "vendor", "version", "status", "effective_from"]
    )
    for e in entries:
        writer.writerow(
            [
                e.id,
                e.source,
                e.request_id,
                e.name,
                e.vendor,
                e.version,
                e.status,
                e.effective_from.isoformat() if e.effective_from else "",
            ]
        )
    return output.getvalue()
