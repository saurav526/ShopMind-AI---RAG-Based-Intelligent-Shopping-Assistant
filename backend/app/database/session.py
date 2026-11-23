"""SQLAlchemy database engine and session factory with PostgreSQL primary and SQLite fallback."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import DATA_DIR, logger, settings

DATA_DIR.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


def _build_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql"):
        try:
            eng = create_engine(db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
            with eng.connect() as conn:
                pass
            logger.info("Connected to PostgreSQL database successfully.")
            return eng
        except Exception as exc:
            if settings.USE_SQLITE_FALLBACK:
                logger.warning(
                    f"PostgreSQL connection unavailable ({exc}); falling back to SQLite at {settings.SQLITE_FALLBACK_URL}"
                )
                db_url = settings.SQLITE_FALLBACK_URL
            else:
                raise
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    eng = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
    if db_url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return eng


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
