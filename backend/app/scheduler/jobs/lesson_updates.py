from app.features.lesson_updates.service.schedule import scan_all
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await scan_all(ctx.production)
