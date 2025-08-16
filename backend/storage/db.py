from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import get_settings

# Resolve database URL (env > default SQLite under backend/data/db)
settings = get_settings()
DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[2] / "data" / "db" / "finance_app.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"
DATABASE_URL = settings.DATABASE_URL or DEFAULT_SQLITE_URL

# Ensure SQLite directory exists
if DATABASE_URL.startswith("sqlite"):
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Engine options
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

# SQLite pragmas for reliability & performance
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def init_db():
    # Import models to register metadata, then create tables
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
