from datetime import UTC, datetime

from app.features.reading_stack.service.schedule import run_reading_stack
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_reading_stack(ctx.daily.radar.research, datetime.now(UTC))
