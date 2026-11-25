"""Task "Weekly radar reading" (P10, D160): every 15 minutes and at startup, on Monday from 06:00
local
time, each account receives a market reading, once per local ISO week. The work is in the `radar`
feature (`run_weekly_radar`), which never imports this package (contract 8): the task only unpacks
its context and reads the time."""

from datetime import UTC, datetime

from app.features.radar.service.schedule import run_weekly_radar
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_weekly_radar(ctx.daily.radar, datetime.now(UTC))
