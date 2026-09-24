"""Compatibility wrapper used by the API layer for DB access."""

from app.db.database import Base, SessionLocal, engine, get_db, get_tidb_url, init_db

__all__ = ["Base", "SessionLocal", "engine", "get_db", "get_tidb_url", "init_db"]
