"""Task "Mini project statements" (P1, D166): every 15 minutes and at startup, each non-skipped
module
of a validated program whose week has started receives its project and the Practitioner's
statement. The work is in the `projects` feature (`ensure_project_briefs`), which never imports this
package (contract 8): the task only unpacks its context and reads the time. At startup, the same
pass repairs the projects whose session died (status that follows the session)."""

from datetime import UTC, datetime

from app.features.projects.service.briefs import ensure_project_briefs
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    await ensure_project_briefs(ctx.daily.projects, datetime.now(UTC))
