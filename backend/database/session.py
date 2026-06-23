"""
NeuroGuard AI - Database Session Management
=============================================
=============================================
Database engine configuration and session factory.
Supports PostgreSQL (with pgvector) and SQLite (legacy fallback).
"""

import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import text, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.database.models import Base

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    """Extract the file path from the SQLite URL and ensure the directory exists."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_url


# Configure connect_args based on dialect
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create engine
engine = create_engine(
    _get_db_path(),
    connect_args=connect_args,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)


# Enable WAL mode and foreign keys for SQLite (better concurrent read performance)
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all database tables. Safe to call multiple times."""
    # Ensure pgvector extension exists before creating tables if using postgres
    if settings.DATABASE_URL.startswith("postgresql"):
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified successfully")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session after the request.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
