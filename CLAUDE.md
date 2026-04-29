# SysIntro – Coding Conventions

## Architecture
- **Routes are thin** – API routes validate input/output only; all business logic lives in `app/services/`.
- **Services own writes** – only service functions call `session.add()`, `session.commit()`, `session.delete()`. Routes call services, never touch ORM objects directly.
- **One concept per file** – each model, schema, service, and route module covers exactly one domain concept.

## Python style
- Python 3.11+. Use `from __future__ import annotations` at the top of every module.
- Type hints on all function signatures.
- Pydantic v2 patterns (`model_config`, `model_validator`, `field_validator`).
- No `print()` in app code (only seed/CLI scripts). Use `logging` instead.
- Run `ruff check .` clean before committing.

## Security rules (enforced by code, not convention)
- Argon2 for all passwords – no other hash function.
- JWT in HttpOnly + SameSite=Lax cookie; `SECURE_COOKIES=1` in prod.
- CSRF double-submit cookie on all non-GET web routes.
- Rate-limit `/auth/login` at 5/min/ip via SlowAPI.
- No stack traces in production responses – `errors.py` generic handler.
- Audit log is append-only; no UPDATE/DELETE paths exist.
- File uploads: 25 MB max, MIME whitelist, filename sanitised, stored as `<uuid>.<ext>`.
- SECRET_KEY from env only.

## Database
- SQLite with WAL mode (`PRAGMA journal_mode=WAL`).
- Alembic manages all schema changes. Never `Base.metadata.create_all()` in app code.
- All queries via SQLAlchemy ORM. No raw SQL except in tests/seeds.

## References
- Functional spec: `SPEC.md`
- Data model & enums: `app/models/`
- Business rules: `app/services/`
