"""The "D-7" task (SPEC 3.5, D91): every 15 minutes and at startup, each validated program
has its lesson chain restarted if needed (`ensure_lessons`: week that starts within
7 days at most, interrupted lesson failed, retry of a failed lesson). The D-7 rule is
judged to the day; the short cadence is there to quickly resume a chain stopped outside the port.
With nothing due, a run only reads the database. Without a `jobs` table (phase 8): the lessons'
state is enough for idempotence. A failure on one program does not stop the others. Logs:
identifiers and error type only."""

import logging

from app.features.lessons.service.production import ensure_lessons, list_programs_due
from app.scheduler.base import JobContext

logger = logging.getLogger(__name__)


async def run(ctx: JobContext) -> None:
    programs = await list_programs_due(ctx.session_factory)
    launched = 0
    for user_id, program_id in programs:
        try:
            launched += await ensure_lessons(ctx.production, user_id, program_id) is not None
        except Exception as exc:
            logger.warning(
                "Lessons D-7: program %s not processed (%s)", program_id, type(exc).__name__
            )
    # An empty run every 15 minutes does not deserve an INFO line.
    level = logging.INFO if launched else logging.DEBUG
    logger.log(level, "Lessons D-7: %d program(s), %d lesson(s) launched", len(programs), launched)
