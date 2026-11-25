"""Task "Follow-ups" (SPEC 6.2, D140): every hour and at startup, adopts each account's CV versions,
then synchronises its expected follow-ups. The work is in the `applications` feature
(`run_reminders`), which never imports this package (contract 8): the task only unpacks its
context and reads the time."""

from app.features.applications.service.reminders import run_reminders
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await run_reminders(ctx.applications, ctx.applications.now())
