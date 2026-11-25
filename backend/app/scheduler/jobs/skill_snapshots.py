"""Task "Skill snapshots" (SPEC F15, D106): every 15 minutes and at startup, one record of levels
per
user and per local week (the first pass of the week writes it, `INSERT … ON CONFLICT DO NOTHING`).
The progress curve (5.10) reads them."""

from datetime import UTC, datetime

from app.features.skills.service import write_weekly_snapshots
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await write_weekly_snapshots(ctx.session_factory, datetime.now(UTC))
