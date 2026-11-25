"""Runs and verifications in the sandbox (P5 to P7). Only one at a time per user; the output
is read by byte offset; the end (status, full output, error signature) is frozen at the first
read that sees it. A user's code never runs here: only the sandbox executes it. The output is
never logged."""

import logging
from typing import Any, cast

from app.db.base import utcnow
from app.db.models.ide import IdeRun, IdeSession
from app.features.ide.repository import ExerciseRepository, RunRepository
from app.features.ide.schemas import RunProgress, RunStatus
from app.features.ide.service import sessions
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import (
    entry_missing,
    run_in_progress,
    run_not_found,
    run_refused,
    sandbox_unavailable,
)
from app.features.ide.service.ghost import record_finished_check
from app.features.ide.service.signature import error_signature
from app.features.skills.service import SkillsService
from app.providers.sandbox.base import (
    MAX_TIMEOUT_S,
    CodeSandbox,
    SandboxJob,
    SandboxKind,
    SandboxProgress,
    UnknownRun,
)

logger = logging.getLogger(__name__)

JOB_TIMEOUT_S = 10  # real duration requested from the sandbox (it caps at 15)
PROOF_LABEL = "Completed exercise "
RECENT_RUNS = 20


def _sandbox(ctx: IdeContext) -> CodeSandbox:
    if ctx.sandbox is None:
        raise sandbox_unavailable()
    return ctx.sandbox


async def _poll(ctx: IdeContext, run_id: str, offset: int) -> SandboxProgress | None:
    """What the sandbox returns; `None` if it does not know the job (cleaned up or never sent)."""
    try:
        return await _sandbox(ctx).poll(run_id, offset)
    except UnknownRun:
        return None
    except OSError:
        raise sandbox_unavailable() from None


def _clean(text: str) -> str:
    """The code's output is hostile: NUL is replaced by `?` (a single byte like it, so that the
    sandbox's offsets stay valid); the front end displays it as text."""
    return text.replace("\x00", "?")


def _chunk(output: str, after: int) -> tuple[str, int]:
    """The output from byte `after` (UTF-8), and the next offset."""
    data = output.encode()
    return data[after:].decode(errors="ignore"), len(data)


async def _record_pass(ctx: IdeContext, session: IdeSession) -> None:
    """First successful verification: the session is passed, and the exercise's skill (its
    subject, otherwise its title) earns "ide" evidence, never beyond "in progress"."""
    if session.passed_at is None:
        session.passed_at = utcnow()
    names: list[str] = []
    if session.exercise_id is not None:  # deleted since: the session keeps its title
        exercise = await ExerciseRepository(ctx.db, ctx.user_id).get(session.exercise_id)
        if exercise is not None:
            names = [name for name in (exercise.topic, exercise.title) if name]
    skills = SkillsService(ctx.db, ctx.user_id)
    for name in [*names, session.title]:
        skill_id = await skills.skill_id_for(name)
        if skill_id is not None:
            await skills.add_proof(skill_id, "ide", f"{PROOF_LABEL}{session.title}", session.id)
            return


async def _freeze(ctx: IdeContext, run: IdeRun, progress: SandboxProgress | None) -> None:
    """Freezes the end of a run: status, code, duration, full output, error signature."""
    session = await sessions.get(ctx, run.session_id)
    if progress is None or progress.result is None:
        run.status = "error"
    else:
        result = progress.result
        run.status = result.status
        run.exit_code = result.exit_code
        run.duration_ms = result.duration_ms
        run.truncated = result.truncated
        run.output = _clean(progress.output)
        run.error_signature = error_signature(run.output, set(session.files))
    await ctx.db.flush()
    logger.info("Run %s finished: %s", run.id, run.status)
    # Only a verification by January validates the exercise: Claude's does not count.
    if run.kind == "check" and run.status == "done" and run.origin == "app":
        if run.exit_code == 0:
            await _record_pass(ctx, session)
            await ctx.db.flush()
        if run.exit_code is not None and session.exercise_id is not None:
            await record_finished_check(ctx.db, run)


async def _settle(ctx: IdeContext, run: IdeRun) -> bool:
    """Polls the sandbox for a run in progress; freezes it if finished. True if finished."""
    progress = await _poll(ctx, run.id, 0)
    if progress is not None and progress.result is None:
        return False
    await _freeze(ctx, run, progress)
    return True


async def start(
    ctx: IdeContext,
    session_id: str,
    kind: SandboxKind,
    entry: str | None,
    *,
    source: str | None = None,
    notebook_cell: dict[str, Any] | None = None,
) -> IdeRun:
    session = await sessions.get(ctx, session_id)
    sandbox = _sandbox(ctx)
    repo = RunRepository(ctx.db, ctx.user_id)
    for running in await repo.running():
        if not await _settle(ctx, running):
            raise run_in_progress(running.id)
    wanted = entry or session.entry
    if wanted not in session.files:
        raise entry_missing()
    run = await repo.add(
        session_id=session.id,
        kind=kind,
        entry=wanted,
        requested_by=ctx.caller.label,
        origin=ctx.caller.kind,
        notebook_cell=notebook_cell,
    )
    job = SandboxJob(
        run_id=run.id,
        files={str(path): str(text) for path, text in session.files.items()},
        entry=wanted,
        kind=kind,
        timeout_s=MAX_TIMEOUT_S if kind == "terminal" else JOB_TIMEOUT_S,
        source=source,
        model_user=ctx.user_id if ctx.caller.kind == "app" and kind != "check" else None,
    )
    try:
        await sandbox.submit(job)
    except ValueError:
        raise run_refused() from None
    except OSError:
        raise sandbox_unavailable() from None
    return run


async def progress(
    ctx: IdeContext,
    run_id: str,
    after: int,
    *,
    kind: SandboxKind | None = None,
    persist: bool = True,
) -> RunProgress:
    """The output from byte `after`. End seen = everything frozen (full output, signature)."""
    run = await RunRepository(ctx.db, ctx.user_id).get_fresh(run_id)
    allowed = ("run", "check") if kind is None else (kind,)
    if run is None or run.kind not in allowed:
        raise run_not_found()
    if run.status == "running":
        live = await _poll(ctx, run.id, after)
        if not persist or (live is not None and live.result is None):
            return _live_progress(run.id, live, after)
        await _settle_with(ctx, run, live)
    text, end = _chunk(run.output, after)
    return RunProgress(
        id=run.id,
        status=cast(RunStatus, run.status),
        output=text,
        next_offset=end,
        exit_code=run.exit_code,
        duration_ms=run.duration_ms,
        truncated=run.truncated,
    )


def _live_progress(run_id: str, live: SandboxProgress | None, after: int) -> RunProgress:
    if live is None:
        return RunProgress(
            id=run_id,
            status="error",
            output="",
            next_offset=after,
            exit_code=None,
            duration_ms=None,
            truncated=False,
        )
    result = live.result
    return RunProgress(
        id=run_id,
        status=result.status if result else "running",
        output=_clean(live.output),
        next_offset=live.next_offset,
        exit_code=result.exit_code if result else None,
        duration_ms=result.duration_ms if result else None,
        truncated=result.truncated if result else False,
    )


async def _settle_with(ctx: IdeContext, run: IdeRun, live: SandboxProgress | None) -> None:
    """Freezes a run whose end has just been seen: re-reads the full output (the log is
    complete as soon as the end is visible)."""
    full = await _poll(ctx, run.id, 0) if live is not None else None
    await _freeze(ctx, run, full)


async def list_for(ctx: IdeContext, session_id: str) -> list[IdeRun]:
    """The session's last `RECENT_RUNS` runs (the page re-reads them all every 3 s)."""
    session = await sessions.get(ctx, session_id)
    return await RunRepository(ctx.db, ctx.user_id).recent_of_session(session.id, RECENT_RUNS)
