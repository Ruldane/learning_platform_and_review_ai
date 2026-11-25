"""Durable purge of a Google account's index, even once its session is closed."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.account.repository import complete_vector_purge, pending_vector_purges
from app.features.memory.service.indexer import MemoryIndexer
from app.providers.vector.base import VectorStoreUnavailable

logger = logging.getLogger(__name__)


async def finish_vector_purge(
    factory: async_sessionmaker[AsyncSession], indexer: MemoryIndexer, user_id: str
) -> bool:
    """Acknowledges the work after the purge. On shutdown or failure, it stays replayable."""
    try:
        await indexer.purge_retired_user(user_id)
        async with factory.begin() as db:
            await complete_vector_purge(db, user_id)
    except (VectorStoreUnavailable, SQLAlchemyError) as exc:
        logger.warning("Vector purge pending: user=%s type=%s", user_id, type(exc).__name__)
        return False
    return True


async def retry_vector_purges(
    factory: async_sessionmaker[AsyncSession], indexer: MemoryIndexer
) -> None:
    async with factory() as db:
        pending = await pending_vector_purges(db)
    for user_id in pending:
        await finish_vector_purge(factory, indexer, user_id)
