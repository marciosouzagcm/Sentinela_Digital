from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def get_tidb_url() -> str:
    """Build a TiDB-compatible SQLAlchemy URL from environment variables."""
    return (
        os.getenv("TIDB_URL")
        or "mysql+pymysql://root:@127.0.0.1:4000/sentinela?charset=utf8mb4"
    )


def create_tidb_engine() -> Engine:
    """Create a connection pool tuned for TiDB Serverless/Cluster endpoints."""
    database_url = get_tidb_url()
    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
        echo=False,
        connect_args={"connect_timeout": 5, "autocommit": True},
    )


engine = create_tidb_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables defined by SQLAlchemy models in the application."""
    from app.db.models import User  # type: ignore  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Light warm-up check: keep TiDB health checks cheap and optional.
try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
except Exception:
    pass
