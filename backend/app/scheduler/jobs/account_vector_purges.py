"""Reprend la purge vectorielle des comptes Google déjà effacés."""

from app.features.account.service.vector_purges import retry_vector_purges
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await retry_vector_purges(ctx.session_factory, ctx.daily.projects.memory.indexer)
