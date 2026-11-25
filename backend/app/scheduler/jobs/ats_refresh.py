"""Task "ATS refresh" (P14, D158): every 6 hours and at startup, each account whose last refresh is
30 days old or more receives a `web_research` session on how ATS work. The work is in the `cv`
feature (`run_ats_refresh`), which never imports this package (contract 8): the task only unpacks
its context and reads the time."""

from datetime import UTC, datetime

from app.features.cv.service.ats_refresh import run_ats_refresh
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_ats_refresh(ctx.session_factory, ctx.launcher, datetime.now(UTC))
