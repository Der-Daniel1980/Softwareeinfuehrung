from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import BitFcCategory

BIT_FC_CATEGORIES = [
    {"name": "Labor", "description": "Labor- und Diagnostiksysteme"},
    {"name": "Diagnostik", "description": "Diagnostische Informationssysteme"},
    {"name": "Radiologie", "description": "Radiologische Informationssysteme (RIS/PACS)"},
    {"name": "Personal & HR", "description": "Personal- und Ressourcenmanagement"},
    {"name": "Finanzen", "description": "Finanz- und Buchhaltungssysteme"},
    {"name": "IT-Infrastruktur", "description": "IT-Infrastruktur und Querschnittssysteme"},
]


def seed_bit_fc(session: Session) -> None:
    for data in BIT_FC_CATEGORIES:
        existing = session.query(BitFcCategory).filter(BitFcCategory.name == data["name"]).first()
        if not existing:
            session.add(BitFcCategory(**data))
    session.flush()
