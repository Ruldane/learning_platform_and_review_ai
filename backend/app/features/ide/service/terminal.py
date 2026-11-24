"""Terminal relay. No command is interpreted in the IDE service."""

from app.core.errors import AppError
from app.db.models.ide import IdeRun
from app.features.ide.repository import RunRepository
from app.features.ide.schemas import RunProgress
from app.features.ide.schemas_terminal import TerminalStarted
from app.features.ide.service import runs
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import run_not_found, sandbox_unavailable
from app.providers.sandbox.base import MAX_INPUT_CHUNK_BYTES, CodeSandbox, UnknownRun


def _sandbox(ctx: IdeContext) -> CodeSandbox:
    if ctx.sandbox is None:
        raise sandbox_unavailable()
    return ctx.sandbox


async def _owned(ctx: IdeContext, run_id: str) -> IdeRun:
    found = await RunRepository(ctx.db, ctx.user_id).get_fresh(run_id)
    if found is None or found.kind != "terminal":
        raise run_not_found()
    return found


def _closed() -> AppError:
    return AppError("terminal_closed", "This terminal is closed.", 409)


async def start(ctx: IdeContext, session_id: str) -> TerminalStarted:
    run = await runs.start(ctx, session_id, "terminal", None)
    return TerminalStarted(id=run.id)


async def read(ctx: IdeContext, run_id: str, offset: int) -> RunProgress:
    return await runs.progress(
        ctx, run_id, offset, kind="terminal", persist=ctx.caller.kind == "app"
    )


async def send(ctx: IdeContext, run_id: str, text: str) -> None:
    run = await _owned(ctx, run_id)
    if run.status != "running":
        raise _closed()
    try:
        data = text.encode()
        if not 0 < len(data) <= MAX_INPUT_CHUNK_BYTES:
            raise ValueError("invalid size")
        await _sandbox(ctx).write_input(run.id, data)
    except UnknownRun:
        raise _closed() from None
    except ValueError:
        raise AppError("terminal_input_invalid", "Input too long or unreadable.", 422) from None
    except OSError:
        raise sandbox_unavailable() from None


async def cancel(ctx: IdeContext, run_id: str) -> None:
    run = await _owned(ctx, run_id)
    if run.status == "running":
        try:
            await _sandbox(ctx).cancel(run.id)
        except OSError:
            raise sandbox_unavailable() from None
