"""
SQLAlchemy engine/session setup.

This module is PostgreSQL-oriented (per Qualyx architecture direction).
The connection string is fully driven by configuration/environment
variables (see app/config.py) so no environment-specific values are
hard-coded here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Shared declarative base for all Claude-2-owned ORM models."""
    pass


def get_db() -> Session:
    """
    FastAPI dependency that yields a database session and guarantees
    it is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Local-development convenience only: creates tables directly from
    the ORM models if they don't exist yet.

    This is NOT a replacement for real migrations. Once the schema
    stabilizes across contracts, this should be replaced by Alembic
    migrations rather than being relied on long-term.
    """
    from app import models  # noqa: F401  (ensures models are registered on Base)

    Base.metadata.create_all(bind=engine)
