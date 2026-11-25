"""Task "Weekly review" (SPEC F13, 11.4; D106): every 15 minutes and at startup, each validated
program whose review time has passed for January receives its review of the week (once) and a
replanning proposal. The work is in the `replan` feature (`run_weekly_reviews`), which never
imports this package (contract 8): the task only unpacks its context and reads the time."""

from datetime import UTC, datetime

from app.features.replan.service.weekly import run_weekly_reviews
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_weekly_reviews(ctx.session_factory, ctx.replan, datetime.now(UTC))
