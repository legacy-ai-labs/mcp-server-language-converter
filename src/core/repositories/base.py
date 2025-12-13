"""Base repository with common CRUD operations."""

from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base


class BaseRepository[ModelType: Base]:
    """Base repository for common database operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model: type[ModelType] = model
        self.session: AsyncSession = session

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create a new record.

        Args:
            data: Data dictionary for creating the record

        Returns:
            Created model instance
        """
        # SQLAlchemy models are dynamically constructed; help mypy with type annotation.
        instance: ModelType = self.model(**data)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id_: int) -> ModelType | None:
        """Get a record by ID.

        Args:
            id_: Record ID

        Returns:
            Model instance or None if not found
        """
        primary_keys = inspect(self.model).primary_key
        if not primary_keys:
            raise ValueError(f"Model {self.model.__name__} has no primary key")

        # Use first PK column (common case); avoids assuming an `.id` attribute exists.
        pk_column = primary_keys[0]
        result = await self.session.execute(select(self.model).where(pk_column == id_))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ModelType]:
        """List all records.

        Returns:
            List of all model instances
        """
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def update(self, id_: int, data: dict[str, Any]) -> ModelType | None:
        """Update a record.

        Args:
            id_: Record ID
            data: Data dictionary with fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get_by_id(id_)
        if not instance:
            return None

        for key, value in data.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)

        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id_: int) -> bool:
        """Delete a record.

        Args:
            id_: Record ID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id_)
        if not instance:
            return False

        await self.session.delete(instance)
        await self.session.commit()
        return True
