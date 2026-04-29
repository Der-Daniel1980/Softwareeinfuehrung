"""Idempotent seed script for demo data.

Run with:
    python -m app.seed.run_seed
    python -m app.seed.run_seed --reset-admin-password
"""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument(
        "--reset-admin-password",
        action="store_true",
        help="Reset admin@demo.local password to demo1234",
    )
    args = parser.parse_args()

    # Import here so the module can be imported without DB being ready
    from app.database import SessionLocal
    from app.seed.bit_fc import seed_bit_fc
    from app.seed.fields import seed_fields
    from app.seed.roles import seed_roles
    from app.seed.system_categories import seed_system_categories
    from app.seed.users import seed_users

    session = SessionLocal()
    try:
        print("Seeding roles...")
        seed_roles(session)
        session.flush()

        print("Seeding users...")
        seed_users(session, reset_admin_password=args.reset_admin_password)
        session.flush()

        print("Seeding BIT/FC categories...")
        seed_bit_fc(session)
        session.flush()

        print("Seeding system categories...")
        seed_system_categories(session)
        session.flush()

        print("Seeding fields...")
        seed_fields(session)

        session.commit()
        print("Seed complete.")
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
