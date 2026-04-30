from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import BitFcCategory

# amedes-spezifische Business-IT- bzw. Fachbereichs-Kategorien.
# Migration 0002 entfernt Altbestand; dieser Seed legt den finalen Satz an.
BIT_FC_CATEGORIES = [
    {"name": "BIT Enterprise",
     "description": "Übergreifende Enterprise-Anwendungen (ERP, CRM, Office, Mail …)"},
    {"name": "BIT Lab",
     "description": "Labor- und Diagnostiksysteme (LIS, LIMS, …)"},
    {"name": "Digital Security",
     "description": "Sicherheits- und Identitätsdienste, IAM, MDR/EDR, SIEM"},
    {"name": "BIT CLM & Genetics",
     "description": "Clinical Lab Management & Humangenetik (Module)"},
    {"name": "IT Operations",
     "description": "IT-Betrieb, Infrastruktur, Monitoring, Service Management"},
    {"name": "Digital Processes",
     "description": "Workflow-/BPM-Tools, RPA, ECM, Dokumentenautomation"},
    {"name": "BIT Enterprise Data & Intelligence",
     "description": "Data Warehouse, BI-/Analytics-Plattformen, Data Science"},
]


def seed_bit_fc(session: Session) -> None:
    for data in BIT_FC_CATEGORIES:
        existing = session.query(BitFcCategory).filter(BitFcCategory.name == data["name"]).first()
        if existing:
            existing.description = data["description"]
        else:
            session.add(BitFcCategory(**data))
    session.flush()
