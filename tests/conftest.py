from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///./data/test_sysintro.db"

# Set env before importing app modules
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only"
os.environ["SECURE_COOKIES"] = "0"
os.environ["DEBUG"] = "1"
os.environ["TESTING"] = "1"  # Disables slowapi rate limiting


from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

# Create test engine
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _setup_db():
    """Create all tables and run seed."""
    import os
    os.makedirs("data", exist_ok=True)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    from app.seed.bit_fc import seed_bit_fc
    from app.seed.fields import seed_fields
    from app.seed.roles import seed_roles
    from app.seed.system_categories import seed_system_categories
    from app.seed.users import seed_users

    session = TestingSessionLocal()
    try:
        seed_roles(session)
        session.flush()
        seed_users(session)
        session.flush()
        seed_bit_fc(session)
        session.flush()
        seed_system_categories(session)
        session.flush()
        seed_fields(session)
        session.commit()
    finally:
        session.close()


# Run once per session
_setup_db()


@pytest.fixture(scope="session")
def db_engine():
    return test_engine


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def client():
    return TestClient(app, raise_server_exceptions=True)


def _login(client: TestClient, email: str, password: str = "demo1234") -> TestClient:
    """Login and return a client with the auth cookie set."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return client


@pytest.fixture(scope="session")
def as_admin(client):
    return _login(client, "admin@demo.local")


@pytest.fixture(scope="session")
def as_requester(client):
    return _login(client, "requester@demo.local")


@pytest.fixture(scope="session")
def as_br(client):
    return _login(client, "br@demo.local")


@pytest.fixture(scope="session")
def as_itsec(client):
    return _login(client, "itsec@demo.local")


@pytest.fixture(scope="session")
def as_dsb(client):
    return _login(client, "dsb@demo.local")


@pytest.fixture(scope="session")
def as_appmgr(client):
    return _login(client, "appmgr@demo.local")


@pytest.fixture(scope="session")
def as_appop(client):
    return _login(client, "appop@demo.local")


@pytest.fixture(scope="session")
def as_lic(client):
    return _login(client, "lic@demo.local")


@pytest.fixture(scope="session")
def as_auditor(client):
    return _login(client, "auditor@demo.local")


def as_role(client: TestClient, code: str) -> TestClient:
    """Helper: login as demo user for the given role code."""
    email_map = {
        "ADMIN": "admin@demo.local",
        "REQUESTER": "requester@demo.local",
        "BETRIEBSRAT": "br@demo.local",
        "IT_SECURITY": "itsec@demo.local",
        "DATA_PROTECTION": "dsb@demo.local",
        "APP_MANAGER": "appmgr@demo.local",
        "APP_OPERATION": "appop@demo.local",
        "LICENSE_MGMT": "lic@demo.local",
        "AUDITOR": "auditor@demo.local",
    }
    return _login(client, email_map[code])


def get_test_db():
    return TestingSessionLocal()
