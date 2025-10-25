"""Initialize database - create tables."""

import asyncio
import logging

from src.core.database import init_db

# Import models first so they're registered with Base.metadata
from src.core.models.tool import Tool  # noqa: F401


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialize database tables."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())
