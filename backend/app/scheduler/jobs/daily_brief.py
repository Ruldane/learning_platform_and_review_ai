"""Task "Morning brief" (P12, D162): every 10 minutes and at startup, each account whose brief time
has passed receives the brief of its local day (only once, even if it was already created when the
home page was opened). The work is in the `brief` feature (`run_daily_briefs`), which never imports
this package (contract 8): the task only unpacks its context and reads the time."""

from datetime import UTC, datetime

from app.features.brief.service.schedule import run_daily_briefs
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_daily_briefs(ctx.daily.brief, datetime.now(UTC))
