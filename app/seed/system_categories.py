from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import SystemCategoryDefinition

SYSTEM_CATEGORIES = [
    {
        "code": "A",
        "label": "Kategorie A – Keine Mitbestimmung",
        "description": (
            "Eine Leistungs- und/oder Verhaltenskontrolle ist technisch nicht möglich "
            "oder wird durch entsprechende Konfiguration dauerhaft unterbunden und es ist "
            "auch kein anderes Mitbestimmungsrecht berührt. Betriebsrats-Freigabe erfolgt "
            "als Kenntnisnahme."
        ),
        "requires_bv_attachment": False,
        "requires_post_approval": False,
        "expedited": False,
    },
    {
        "code": "B",
        "label": "Kategorie B – Reguläre BR-Prüfung",
        "description": (
            "Eine Leistungs- und/oder Verhaltenskontrolle ist zwar technisch möglich, "
            "wird aber nicht bezweckt. Reguläre BR-Freigabe erforderlich. Hinweis: "
            "Nicht-Bezweckung schriftlich bestätigt? Konfigurations-Nachweis vorhanden?"
        ),
        "requires_bv_attachment": False,
        "requires_post_approval": False,
        "expedited": False,
    },
    {
        "code": "C",
        "label": "Kategorie C – Erweiterter BR-Workflow (BV erforderlich)",
        "description": (
            "Die technische Einrichtung/Software ist zur Leistungs- und/oder "
            "Verhaltenskontrolle bestimmt. Erweiterter BR-Workflow. Voraussetzung: "
            "Abschluss einer separaten Betriebsvereinbarung. Die unterzeichnete BV "
            "muss als Anhang hochgeladen werden."
        ),
        "requires_bv_attachment": True,
        "requires_post_approval": False,
        "expedited": False,
    },
    {
        "code": "D",
        "label": "Kategorie D – Notfall/Expedited (vorläufig freigegeben)",
        "description": (
            "Aus sicherheitstechnischen Gründen umgehend erforderlich – amedes setzt um, "
            "GBR wird nachträglich informiert. Antrag erhält sofort Status 'Vorläufig "
            "freigegeben'. Nachgenehmigung durch GBR mit Frist (30 Tage). "
            "Vier-Augen-Prinzip: Application Owner und IT Application Owner müssen "
            "gemeinsam bestätigen."
        ),
        "requires_bv_attachment": False,
        "requires_post_approval": True,
        "expedited": True,
    },
]


def seed_system_categories(session: Session) -> None:
    for data in SYSTEM_CATEGORIES:
        existing = session.get(SystemCategoryDefinition, data["code"])
        if not existing:
            session.add(SystemCategoryDefinition(**data))
    session.flush()
