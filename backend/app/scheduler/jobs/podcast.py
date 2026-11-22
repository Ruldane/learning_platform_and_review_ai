from datetime import UTC, datetime

from app.features.podcast.service.scheduling import run_daily_podcasts
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_daily_podcasts(ctx.daily.podcast, datetime.now(UTC))
