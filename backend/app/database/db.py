"""
Database setup for the Smart Tire Analyzer backend.
"""

import asyncio
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from app.config import settings
    _default_db_url = f"sqlite+aiosqlite:///{Path(__file__).resolve().parents[1] / 'smart_tire.db'}"
except ImportError:
    _default_db_url = "sqlite+aiosqlite:///./smart_tire.db"

DATABASE_URL = os.getenv("DATABASE_URL", _default_db_url)

_engine_kwargs: dict = {
    "echo": False,
    "future": True,
    "connect_args": {"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
}
if "postgresql" in DATABASE_URL:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()
_db_ready = False
_db_ready_lock = asyncio.Lock()


async def get_db():
    """Dependency for FastAPI route handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ensure_database_ready(force: bool = False) -> None:
    """Create tables if they are missing."""
    global _db_ready
    if _db_ready and not force:
        return

    async with _db_ready_lock:
        if _db_ready and not force:
            return

        # Import models lazily so metadata is populated before create_all.
        from app.database import models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _db_ready = True
