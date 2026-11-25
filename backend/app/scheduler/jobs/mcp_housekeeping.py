"""Task "MCP housekeeping" (phase 10, P15, P19): every 10 minutes and at startup, « À confirmer »
requests whose time has passed become "expired" (they will never run); then the call journal, the
change history and the closed requests older than 30 days are purged (they keep text: nothing stays
beyond that). It also catches up on the indexing of memory items left with an empty `indexed_at`
(direct MCP writes, after a restart before the background task), in bounded batches: embeddings
only, no model call. The work is in the `mcp` and `memory` features; the task only unpacks its
context and reads the time."""

from datetime import UTC, datetime

from app.features.mcp.service.calls import purge_old_calls
from app.features.mcp.service.changes import purge_old_changes
from app.features.mcp.service.confirmation_support import purge_closed_confirmations
from app.features.mcp.service.confirmations import expire_due
from app.features.memory.service.direct import index_pending_all
from app.features.sessions.service import expire_steps
from app.scheduler.base import JobContext


async def run(ctx: JobContext) -> None:
    now = datetime.now(UTC)
    await expire_due(ctx.session_factory, now)
    await expire_steps(ctx.session_factory, now)
    await purge_old_calls(ctx.session_factory, now)
    await purge_old_changes(ctx.session_factory, now)
    await purge_closed_confirmations(ctx.session_factory, now)
    # The memory that the daily already carries (projects): nothing to change in `JobContext`.
    await index_pending_all(ctx.daily.projects.memory)
