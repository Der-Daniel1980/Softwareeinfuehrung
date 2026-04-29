from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Role, User

DEMO_PASSWORD = "demo1234"

USERS = [
    {"email": "admin@demo.local", "name": "Admin", "roles": ["ADMIN"]},
    {"email": "requester@demo.local", "name": "Max Mustermann", "roles": ["REQUESTER"]},
    {"email": "br@demo.local", "name": "Britta BR", "roles": ["BETRIEBSRAT"]},
    {"email": "itsec@demo.local", "name": "Ingo IT-Sec", "roles": ["IT_SECURITY"]},
    {"email": "dsb@demo.local", "name": "Diana DSB", "roles": ["DATA_PROTECTION"]},
    {"email": "appmgr@demo.local", "name": "Anna App-Mgr", "roles": ["APP_MANAGER"]},
    {"email": "appop@demo.local", "name": "Otto App-Op", "roles": ["APP_OPERATION"]},
    {"email": "lic@demo.local", "name": "Lars Lizenz", "roles": ["LICENSE_MGMT"]},
    {"email": "auditor@demo.local", "name": "Aud Itor", "roles": ["AUDITOR"]},
    {"email": "owner@demo.local", "name": "Olivia Owner", "roles": ["REQUESTER"]},
]


def seed_users(session: Session, reset_admin_password: bool = False) -> dict[str, User]:
    user_map: dict[str, User] = {}
    for data in USERS:
        user = session.query(User).filter(User.email == data["email"]).first()
        if not user:
            user = User(
                email=data["email"],
                name=data["name"],
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            session.flush()
        elif reset_admin_password and data["email"] == "admin@demo.local":
            user.password_hash = hash_password(DEMO_PASSWORD)
            print(f"Reset password for {data['email']}")

        # Flush so user is in session before roles are assigned
        session.flush()
        # Assign roles
        for role_code in data["roles"]:
            role = session.query(Role).filter(Role.code == role_code).first()
            if role and role not in user.roles:
                user.roles.append(role)

        session.flush()
        user_map[data["email"]] = user

    return user_map
