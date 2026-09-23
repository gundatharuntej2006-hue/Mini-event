"""
Database compatibility layer for EVENT HQ.
Re-exports the shared SQLAlchemy Base, engine, SessionLocal, and get_db dependency.
Does NOT create duplicate database infrastructure.
"""
from app.db.base import Base
from app.db.session import engine, SessionLocal, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
