"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from typing import Any, cast

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, declared_attr, sessionmaker

from src.core.config import get_settings


settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    future=True,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create synchronous engine for thread pool operations
# Convert asyncpg URL to psycopg2 URL for sync operations
sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
sync_engine = create_engine(
    sync_database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create synchronous session factory for thread pool
sync_session_factory = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all database models."""

    metadata = metadata

    @declared_attr.directive  # type: ignore[misc]
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        class_name = cast(str, cls.__name__)
        return class_name.lower() + "s"

    def dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.

    Yields:
        AsyncSession: Database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
