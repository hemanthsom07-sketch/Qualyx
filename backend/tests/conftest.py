"""
Test fixtures.

IMPORTANT / FLAGGED FOR DISCUSSION:
Per the Master Prompt, the backend architecture targets PostgreSQL and we
should not quietly swap the architecture to SQLite for convenience.

This fixture file does NOT change the application's architecture — the
app itself (app/database.py, app/config.py) still targets PostgreSQL by
default. However, for isolated, fast, dependency-free unit tests in this
milestone, we override the `get_db` dependency with an in-memory SQLite
session *only inside the test process*.

This is a common, narrow testing practice (isolating unit tests from a
running database service) rather than an architecture change. That said,
per Task 3's instruction to "clearly report any local dependency/setup
required," this choice is explicitly flagged in the milestone report for
human review. If the team prefers integration tests to run against a real
local PostgreSQL instance instead, this fixture should be updated to point
at a test database via DATABASE_URL rather than SQLite.
"""

import os

# Must be set BEFORE importing app.config/app.main: disables the
# startup-time init_db() call against the (unreachable, in this test
# process) PostgreSQL database. The real app still defaults to
# PostgreSQL/db_auto_create=true outside of tests.
os.environ.setdefault("DB_AUTO_CREATE", "false")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://unused:unused@localhost:5432/unused")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

# StaticPool is required here: SQLite's in-memory database is scoped to a
# single connection. Without StaticPool, SQLAlchemy's default pooling opens
# a new connection per checkout, so create_all() creates the table on one
# connection while the session later reads from a different (empty) one —
# producing "no such table: projects". StaticPool forces every checkout to
# reuse the same underlying connection for the lifetime of this engine.
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
