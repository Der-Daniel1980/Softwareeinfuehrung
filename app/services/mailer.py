from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Notification


def would_send(
    session: Session,
    kind: str,
    recipient_email: str,
    subject: str,
    body: str,
) -> Notification:
    """Record a notification that would be sent (demo: no real SMTP)."""
    n = Notification(
        kind=kind,
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        would_send_at=datetime.utcnow(),
    )
    session.add(n)
    return n
