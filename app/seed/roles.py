from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Role
from app.models.enums import RoleCode

ROLES = [
    {"code": RoleCode.REQUESTER.value, "label": "Antragsteller", "notification_email": None},
    {
        "code": RoleCode.BETRIEBSRAT.value,
        "label": "Betriebsrat",
        "notification_email": "br@demo.local",
    },
    {
        "code": RoleCode.IT_SECURITY.value,
        "label": "IT Sicherheitsbeauftragter",
        "notification_email": "itsec@demo.local",
    },
    {
        "code": RoleCode.DATA_PROTECTION.value,
        "label": "Datenschutzbeauftragter",
        "notification_email": "dsb@demo.local",
    },
    {
        "code": RoleCode.APP_MANAGER.value,
        "label": "Application Manager",
        "notification_email": "appmgr@demo.local",
    },
    {
        "code": RoleCode.APP_OPERATION.value,
        "label": "Application Operation",
        "notification_email": "appop@demo.local",
    },
    {
        "code": RoleCode.LICENSE_MGMT.value,
        "label": "Lizenzmanagement",
        "notification_email": "lic@demo.local",
    },
    {"code": RoleCode.ADMIN.value, "label": "Administrator", "notification_email": None},
    {"code": RoleCode.AUDITOR.value, "label": "Auditor", "notification_email": None},
]


def seed_roles(session: Session) -> dict[str, Role]:
    role_map: dict[str, Role] = {}
    for data in ROLES:
        role = session.query(Role).filter(Role.code == data["code"]).first()
        if not role:
            role = Role(**data)
            session.add(role)
            session.flush()
        role_map[data["code"]] = role
    return role_map
