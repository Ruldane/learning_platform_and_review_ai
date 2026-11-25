import logging
from datetime import UTC, datetime

from app.features.routines.service import run_daily
from app.features.settings.service import scheduled_users
from app.scheduler.base import JobContext

logger = logging.getLogger(__name__)


async def run(ctx: JobContext) -> None:
    async with ctx.session_factory() as db:
        owners = await scheduled_users(db)
    now = datetime.now(UTC)
    for owner in owners:
        try:
            async with ctx.session_factory() as db:
                await run_daily(db, owner, now)
        except Exception as error:
            logger.warning("Routine failed for %s (%s)", owner, type(error).__name__)
