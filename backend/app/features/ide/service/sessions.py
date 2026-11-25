"""Code sessions: the files in progress (at most 20, 200 KB), the entry file, the first
successful verification (`passed_at`)."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.db.base import utcnow
from app.db.models.ide import IdeSession
from app.features.ide.hashing import file_hash, is_file_hash
from app.features.ide.repository import ExerciseRepository, PreferenceRepository, SessionRepository
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import (
    base_hash_required,
    entry_invalid,
    entry_missing,
    exercise_not_found,
    files_changed,
    files_too_large,
    mcp_ide_test_file,
    mcp_ide_write_off,
    mcp_write_one_file,
    session_not_found,
    stale_base,
)
from app.features.ide.service.ghost import exercise_version
from app.providers.sandbox.base import MAX_FILES, MAX_TOTAL_BYTES, check_file_name

logger = logging.getLogger(__name__)

DEFAULT_ENTRY = "main.py"
FREE_TITLE = "Free session"


@dataclass(frozen=True)
class PassedSession:
    id: str
    title: str
    at: datetime


async def get(ctx: IdeContext, session_id: str) -> IdeSession:
    found = await SessionRepository(ctx.db, ctx.user_id).get_fresh(session_id)
    if found is None:
        raise session_not_found()
    return found


async def list_all(ctx: IdeContext) -> list[IdeSession]:
    return await SessionRepository(ctx.db, ctx.user_id).newest_first()


async def open_session(ctx: IdeContext, exercise_id: str | None, title: str | None) -> IdeSession:
    """A session on the exercise's starting files, or a free session (an empty `main.py`).
    Another user's exercise is not found."""
    files: dict[str, str] = {DEFAULT_ENTRY: ""}
    entry = DEFAULT_ENTRY
    name = title or FREE_TITLE
    version = None
    statement = None
    if exercise_id is not None:
        exercise = await ExerciseRepository(ctx.db, ctx.user_id).get(exercise_id)
        if exercise is None:
            raise exercise_not_found()
        entry = exercise.entry
        files = {str(path): str(text) for path, text in exercise.files.items()}
        files.setdefault(entry, "")
        name = title or exercise.title
        version = exercise_version(exercise)
        statement = exercise.statement
    return await SessionRepository(ctx.db, ctx.user_id).add(
        exercise_id=exercise_id,
        title=name,
        files=files,
        entry=entry,
        exercise_version=version,
        exercise_statement=statement,
    )


def check_files(files: dict[str, str], entry: str) -> None:
    """The sandbox's caps (20 files, 200,000 bytes, allowed names) and the entry present."""
    try:
        check_file_name(entry)
    except ValueError:
        raise entry_invalid() from None
    if not files or entry not in files:
        raise entry_missing()
    size = sum(len(text.encode()) for text in files.values())
    if len(files) > MAX_FILES or size > MAX_TOTAL_BYTES:
        raise files_too_large()


async def claim_files(ctx: IdeContext, session: IdeSession) -> bool:
    """Reserves the writing of the files of the session read: the database only grants it if
    nobody has written since the read (`files_version` unchanged). Atomic: of two writes that
    start from the same read, only one goes through. False: re-read the session."""
    read = session.files_version
    taken = await ctx.db.execute(
        update(IdeSession)
        .where(
            IdeSession.id == session.id,
            IdeSession.user_id == ctx.user_id,
            IdeSession.files_version == read,
        )
        .values(files_version=read + 1)
        .execution_options(synchronize_session=False)
    )
    if taken.rowcount == 0:  # type: ignore[attr-defined]
        return False
    set_committed_value(session, "files_version", read + 1)
    return True


def _clashes(session: IdeSession, files: dict[str, str], base_hashes: dict[str, str]) -> list[str]:
    """The files whose server version is no longer that of `base_hashes` and that `files` would
    change (sending the current text erases nothing)."""
    clash: list[str] = []
    for name, base in sorted(base_hashes.items()):
        current = str(session.files.get(name, ""))
        if file_hash(current) != base and files.get(name, "") != current:
            clash.append(name)
    # A file Claude has created since: absent from the snapshot, the upload would erase it.
    known = base_hashes.keys() | files.keys()
    return sorted({*clash, *(name for name in session.files if name not in known)})


async def save_files(
    ctx: IdeContext,
    session_id: str,
    files: dict[str, str],
    entry: str | None,
    base_hashes: dict[str, str] | None = None,
) -> IdeSession:
    """Replaces the files (an interface gesture). The entry stays that of the session unless
    `entry` gives another. `base_hashes` (optional): the version on which each file was edited;
    a file Claude has changed since and that the upload would overwrite gives 409 `stale_base`
    (names only), nothing is written."""
    session = await get(ctx, session_id)
    if base_hashes:
        clash = _clashes(session, files, base_hashes)
        if clash:
            logger.info("stale_base: save refused in session %s", session.id)
            raise files_changed(clash)
    wanted = entry or session.entry
    check_files(files, wanted)
    if not await claim_files(ctx, session):  # someone wrote between the read and here
        await ctx.db.refresh(session)
        raise files_changed(sorted(files))
    session.files = dict(files)
    session.entry = wanted
    session.updated_at = utcnow()
    await ctx.db.flush()
    return session


def is_test_file(name: str) -> bool:
    """A file that pytest collects (`test_*.py`, `*_test.py`) or that configures it
    (`conftest.py`), wherever it is in the session's folders."""
    base = name.rsplit("/", 1)[-1]
    return base == "conftest.py" or (
        base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))
    )


async def write_file_as_claude(
    ctx: IdeContext, session_id: str, files: dict[str, str], base_hash: str | None
) -> IdeSession:
    """Claude (MCP) writes **one** file, the others are kept. Only if January has turned the
    switch on (403 `mcp_ide_write_off`, never any content in the message or the log);
    `base_hash` must be the sha256 of the current content (empty text for a new file),
    otherwise 409 `stale_base`: what January has just typed is never overwritten. The entry does
    not change. In an exercise session, never a test file (403 `mcp_ide_test_file`): those are
    hers."""
    session = await get(ctx, session_id)
    prefs = await PreferenceRepository(ctx.db, ctx.user_id).mine()
    if prefs is None or not prefs.mcp_can_write_files:
        logger.info("mcp_ide_write_off: write refused in session %s", session.id)
        raise mcp_ide_write_off()
    if len(files) != 1:
        raise mcp_write_one_file()
    ((name, text),) = files.items()
    if session.exercise_id is not None and is_test_file(name):
        logger.info("mcp_ide_test_file: write refused in session %s", session.id)
        raise mcp_ide_test_file()
    if not is_file_hash(base_hash):
        raise base_hash_required()
    current = session.files.get(name)
    if base_hash != file_hash("" if current is None else str(current)):
        logger.info("stale_base: write refused in session %s", session.id)
        raise stale_base()
    merged = {**session.files, name: text}
    check_files(merged, session.entry)
    if not await claim_files(ctx, session):
        logger.info("stale_base: concurrent write refused in session %s", session.id)
        raise stale_base()
    session.files = merged
    session.updated_at = utcnow()
    await ctx.db.flush()
    return session


async def recent_passes(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[PassedSession]:
    """The successful sessions (first verification) in `[after, before]`, most recent first
    (activity feed). No file, no output."""
    rows = await SessionRepository(db, user_id).passed_between(after, before, limit)
    return [PassedSession(row.id, row.title, row.passed_at) for row in rows if row.passed_at]
