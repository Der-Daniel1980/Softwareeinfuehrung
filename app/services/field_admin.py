"""Admin-Service für den Fragenkatalog.

Erlaubt Admins das Anlegen, Ändern und Löschen von Feldern (FieldDefinition)
sowie das Verwalten der Rollen-Verantwortlichkeiten je Feld
(FieldResponsibility, kind ∈ {INFO, APPROVAL}).

Routen sind dünn (siehe `app/web/admin_field_pages.py`) – sämtliche Schreib-
operationen laufen über diesen Service, damit Audit-Log und Validierungen
zentral bleiben.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    FieldDefinition,
    FieldResponsibility,
    FieldValue,
    Role,
    User,
)
from app.models.enums import AuditAction, InputType, Responsibility
from app.services import audit

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
"""Erzwingt das `bereich.feldname`-Schema (mind. ein Punkt, lowercase, snake_case)."""


# ---------------------------------------------------------------------------
# Lese-Hilfen
# ---------------------------------------------------------------------------


def list_fields(session: Session) -> list[FieldDefinition]:
    return (
        session.query(FieldDefinition)
        .order_by(FieldDefinition.sort_order, FieldDefinition.id)
        .all()
    )


def list_roles(session: Session) -> list[Role]:
    return session.query(Role).order_by(Role.code).all()


def get_field(session: Session, field_id: int) -> FieldDefinition:
    f = session.get(FieldDefinition, field_id)
    if not f:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feld nicht gefunden")
    return f


# ---------------------------------------------------------------------------
# Validierung
# ---------------------------------------------------------------------------


_ALLOWED_INPUT_TYPES = {t.value for t in InputType}


def _validate_payload(
    *,
    key: str,
    section: str,
    label: str,
    input_type: str,
    enum_values_json: str | None,
    conditional_on_key: str | None,
    conditional_equals: str | None,
) -> list[str]:
    errors: list[str] = []
    if not KEY_RE.match(key or ""):
        errors.append(
            "Feld-Key muss dem Schema 'bereich.feldname' entsprechen "
            "(lowercase, snake_case, mind. ein Punkt)."
        )
    if not section.strip():
        errors.append("Abschnitt darf nicht leer sein.")
    if not label.strip():
        errors.append("Label darf nicht leer sein.")
    if input_type not in _ALLOWED_INPUT_TYPES:
        errors.append(
            f"input_type '{input_type}' ist nicht erlaubt. "
            f"Zulässig: {', '.join(sorted(_ALLOWED_INPUT_TYPES))}."
        )
    if input_type in (InputType.ENUM.value, InputType.ENUM_MULTI.value):
        if not enum_values_json:
            errors.append(
                "Für ENUM/ENUM_MULTI müssen Auswahl-Werte als JSON-Array angegeben werden."
            )
        else:
            try:
                vals = json.loads(enum_values_json)
                if not isinstance(vals, list) or not all(
                    isinstance(v, str) and v for v in vals
                ):
                    errors.append("enum_values muss ein JSON-Array nicht-leerer Strings sein.")
            except json.JSONDecodeError:
                errors.append("enum_values ist kein gültiges JSON.")
    if bool(conditional_on_key) ^ bool(conditional_equals):
        errors.append(
            "conditional_on_key und conditional_equals müssen entweder beide "
            "gesetzt oder beide leer sein."
        )
    return errors


# ---------------------------------------------------------------------------
# Schreib-Operationen
# ---------------------------------------------------------------------------


def create_field(
    session: Session,
    actor: User,
    *,
    key: str,
    section: str,
    label: str,
    help_text: str | None,
    input_type: str,
    enum_values_json: str | None,
    is_required: bool,
    conditional_on_key: str | None,
    conditional_equals: str | None,
    sort_order: int,
    responsibilities: dict[int, str],
    included_in_poc: bool = False,
) -> FieldDefinition:
    """`responsibilities` ist eine Map {role_id: 'INFO' | 'APPROVAL'}.

    Rollen, die nicht in der Map auftauchen, haben keine Verantwortung.
    """
    errs = _validate_payload(
        key=key, section=section, label=label, input_type=input_type,
        enum_values_json=enum_values_json,
        conditional_on_key=conditional_on_key,
        conditional_equals=conditional_equals,
    )
    if session.query(FieldDefinition).filter(FieldDefinition.key == key).first():
        errs.append(f"Feld-Key '{key}' existiert bereits.")
    if errs:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"errors": errs})

    field = FieldDefinition(
        key=key.strip(),
        section=section.strip(),
        label=label.strip(),
        help_text=(help_text or None),
        input_type=input_type,
        enum_values=(enum_values_json or None),
        is_required=bool(is_required),
        conditional_on_key=(conditional_on_key or None),
        conditional_equals=(conditional_equals or None),
        sort_order=int(sort_order or 0),
        included_in_poc=bool(included_in_poc),
    )
    session.add(field)
    session.flush()
    _set_responsibilities(session, field, responsibilities)

    audit.log(
        session, actor, AuditAction.FIELD_UPDATED.value,
        "FieldDefinition", str(field.id),
        {"action": "create", "key": field.key},
    )
    session.flush()
    return field


def update_field(
    session: Session,
    actor: User,
    field_id: int,
    *,
    section: str,
    label: str,
    help_text: str | None,
    input_type: str,
    enum_values_json: str | None,
    is_required: bool,
    conditional_on_key: str | None,
    conditional_equals: str | None,
    sort_order: int,
    responsibilities: dict[int, str],
    included_in_poc: bool = False,
) -> FieldDefinition:
    """Schlüssel (`key`) wird bewusst NICHT veränderbar gemacht — sonst würden
    bestehende `field_values`-Einträge verwaisen. Falls der Key falsch ist:
    Feld duplizieren, alten löschen.
    """
    field = get_field(session, field_id)
    errs = _validate_payload(
        key=field.key, section=section, label=label, input_type=input_type,
        enum_values_json=enum_values_json,
        conditional_on_key=conditional_on_key,
        conditional_equals=conditional_equals,
    )
    if errs:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"errors": errs})

    field.section = section.strip()
    field.label = label.strip()
    field.help_text = help_text or None
    field.input_type = input_type
    field.enum_values = enum_values_json or None
    field.is_required = bool(is_required)
    field.conditional_on_key = conditional_on_key or None
    field.conditional_equals = conditional_equals or None
    field.sort_order = int(sort_order or 0)
    field.included_in_poc = bool(included_in_poc)
    session.flush()

    _set_responsibilities(session, field, responsibilities)

    audit.log(
        session, actor, AuditAction.FIELD_UPDATED.value,
        "FieldDefinition", str(field.id),
        {"action": "update", "key": field.key},
    )
    session.flush()
    return field


def delete_field(session: Session, actor: User, field_id: int) -> None:
    """Nur erlaubt, wenn das Feld noch nirgends befüllt ist (sonst Datenverlust)."""
    field = get_field(session, field_id)

    in_use = (
        session.query(FieldValue)
        .filter(FieldValue.field_key == field.key)
        .first()
    )
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Feld kann nicht gelöscht werden — es existieren bereits Antworten "
            "in laufenden Anträgen. Setzen Sie es stattdessen nur ausgeblendet "
            "(z. B. Hilfetext anpassen, Pflicht entfernen).",
        )

    # Verantwortlichkeiten räumen, dann das Feld
    session.query(FieldResponsibility).filter(
        FieldResponsibility.field_id == field.id
    ).delete(synchronize_session=False)
    session.delete(field)

    audit.log(
        session, actor, AuditAction.FIELD_UPDATED.value,
        "FieldDefinition", str(field_id),
        {"action": "delete", "key": field.key},
    )
    session.flush()


# ---------------------------------------------------------------------------
# Internes
# ---------------------------------------------------------------------------


def _set_responsibilities(
    session: Session,
    field: FieldDefinition,
    role_kind_map: dict[int, str],
) -> None:
    """Sync-Logik: Map {role_id: 'INFO' | 'APPROVAL' | ''} -> DB.

    Ein leerer Wert (oder ein Schlüssel, der nicht in der Map auftaucht) bedeutet
    'keine Verantwortung' und führt zur Löschung der Zeile.
    """
    existing = {
        r.role_id: r
        for r in session.query(FieldResponsibility)
        .filter(FieldResponsibility.field_id == field.id)
        .all()
    }
    role_ids_in_db = {r.id for r in session.query(Role).all()}
    valid_kinds = {Responsibility.INFO.value, Responsibility.APPROVAL.value}

    for role_id, kind in role_kind_map.items():
        if role_id not in role_ids_in_db:
            continue
        kind_norm = (kind or "").strip().upper()
        row = existing.get(role_id)
        if kind_norm in valid_kinds:
            if row:
                row.kind = kind_norm
            else:
                session.add(
                    FieldResponsibility(
                        field_id=field.id, role_id=role_id, kind=kind_norm,
                    )
                )
        else:
            if row:
                session.delete(row)

    # Rollen, die in der Map gar nicht auftauchen, ebenfalls bereinigen.
    untouched_ids: Iterable[int] = set(existing.keys()) - set(role_kind_map.keys())
    for rid in untouched_ids:
        session.delete(existing[rid])
    session.flush()
