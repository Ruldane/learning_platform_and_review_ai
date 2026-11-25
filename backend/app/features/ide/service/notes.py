"""Session notes (P8, P9): hints, explanations, annotations, proposals, references. The internal
professor, Claude (through MCP) and January write through the same service; only the author, taken
from the caller, changes. A proposal replaces a range of lines in a file and carries the hash
(sha256) of the file it read: it applies only if the file has not changed. `accept` and `reject`
are interface gestures (excluded from MCP)."""

from app.core.caller import MCP_CONFIRMED, Caller
from app.db.models.ide import IdeNote, IdeSession, NoteAuthor
from app.features.ide.hashing import is_file_hash
from app.features.ide.repository import NoteRepository
from app.features.ide.schemas import QUESTION_MAX, NoteIn
from app.features.ide.service import sessions
from app.features.ide.service.context import IdeContext, file_hash
from app.features.ide.service.errors import (
    files_too_large,
    mcp_gesture_forbidden,
    not_a_proposal,
    note_closed,
    note_invalid,
    note_not_found,
    note_stale,
)
from app.providers.sandbox.base import MAX_TOTAL_BYTES

# Label of the professor's internal caller (graph `ide_teacher`, 10.A3). An MCP token never
# reaches it: every MCP call is `claude`, whatever the token's label.
PROFESSOR_LABEL = "professor"


def author_of(caller: Caller) -> tuple[NoteAuthor, str | None]:
    """`(author, label)`: Claude carries its token's label, the internal professor and January
    have none."""
    if caller.kind == "mcp":
        return "claude", caller.label[:60]
    return ("professor" if caller.label == PROFESSOR_LABEL else "user"), None


def line_count(text: str) -> int:
    """A file's line count (at least 1: an empty file gets filled)."""
    return max(1, len(text.split("\n")) - (1 if text.endswith("\n") else 0))


def apply_replacement(text: str, start: int, end: int, replacement: str) -> str:
    """Replaces lines `start` to `end` (1-based, inclusive) with `replacement`; a trailing
    newline in the replacement does not add an empty line; an empty replacement deletes
    them."""
    parts = text.split("\n")
    body = replacement[:-1] if replacement.endswith("\n") else replacement
    parts[start - 1 : end] = body.split("\n") if body else []
    return "\n".join(parts)


def _check_place(session: IdeSession, data: NoteIn) -> str | None:
    """The target file (if any) exists and the range fits in it. Returns its content."""
    if data.file_path is None:
        if data.line_start is not None or data.line_end is not None:
            raise note_invalid("Lines require a file.")
        return None
    text = session.files.get(data.file_path)
    if text is None:
        raise note_invalid("This file is not part of the session.")
    start, end = data.line_start, data.line_end
    if end is not None and start is None:
        raise note_invalid("The end line requires a start line.")
    if start is not None:
        last = end if end is not None else start
        if start > last or last > line_count(str(text)):
            raise note_invalid("The target lines are not in the file.")
    return str(text)


def _check_proposal(data: NoteIn, text: str | None) -> None:
    """A proposal: file, range, replacement and valid hash of the file that was read."""
    if text is None or data.line_start is None or data.replacement is None:
        raise note_invalid("A proposal requires a file, a line range and a text.")
    if not is_file_hash(data.base_hash):
        raise note_invalid(
            "A proposal requires the sha256 hash of the file that was read (session file_hashes)."
        )
    if data.base_hash != file_hash(text):
        raise note_stale()


async def add(
    ctx: IdeContext,
    session_id: str,
    data: NoteIn,
    *,
    reference_note_id: str | None = None,
    error_key: str | None = None,
    level: int | None = None,
) -> IdeNote:
    """Adds a note; the author comes from the caller. `reference_note_id`, `error_key` and `level`
    (level of a graded hint) belong to the internal professor, never to a request body."""
    session = await sessions.get(ctx, session_id)
    repo = NoteRepository(ctx.db, ctx.user_id)
    if data.kind != "proposal" and (data.replacement is not None or data.base_hash is not None):
        raise note_invalid("Only a proposal carries a replacement text and a hash.")
    author, label = author_of(ctx.caller)
    if data.kind == "question" and (author != "user" or len(data.content) > QUESTION_MAX):
        raise note_invalid("A question is January's, and fits in 2,000 characters.")
    text = _check_place(session, data)
    if data.kind == "proposal":
        _check_proposal(data, text)
    if reference_note_id is not None and await repo.get(reference_note_id) is None:
        raise note_invalid("The referenced note was not found.")
    return await repo.add(
        session_id=session.id,
        kind=data.kind,
        author=author,
        author_label=label,
        origin=ctx.caller.kind,
        file_path=data.file_path,
        line_start=data.line_start,
        line_end=data.line_end or (data.line_start if data.kind == "proposal" else None),
        content=data.content,
        replacement=data.replacement,
        base_hash=data.base_hash,
        reference_note_id=reference_note_id,
        error_key=error_key,
        level=level,
    )


async def list_for(ctx: IdeContext, session_id: str) -> list[IdeNote]:
    session = await sessions.get(ctx, session_id)
    return await NoteRepository(ctx.db, ctx.user_id).of_session(session.id)


async def get(ctx: IdeContext, note_id: str) -> IdeNote:
    note = await NoteRepository(ctx.db, ctx.user_id).get_fresh(note_id)
    if note is None:
        raise note_not_found()
    return note


async def sweep_stale(ctx: IdeContext, session: IdeSession) -> None:
    """Open proposals whose file changed since it was read become `stale` (after the files are
    saved)."""
    for proposal in await NoteRepository(ctx.db, ctx.user_id).open_proposals(session.id):
        text = session.files.get(proposal.file_path or "")
        if text is None or file_hash(str(text)) != proposal.base_hash:
            proposal.status = "stale"
    await ctx.db.flush()


def _gesture_of_january(ctx: IdeContext) -> None:
    """A proposal is decided in the interface or after an MCP confirmation."""
    if ctx.caller.kind == "mcp" and not MCP_CONFIRMED.get():
        raise mcp_gesture_forbidden()


async def accept(ctx: IdeContext, note_id: str) -> IdeSession:
    """Applies the proposal if its file has not changed; otherwise it becomes `stale` (saved right
    away: the 409 error rolls back the request's transaction)."""
    _gesture_of_january(ctx)
    note = await get(ctx, note_id)
    if note.kind != "proposal":
        raise not_a_proposal()
    if note.status not in ("open", "stale"):
        raise note_closed()
    session = await sessions.get(ctx, note.session_id)
    current = session.files.get(note.file_path or "")
    here = None if current is None else file_hash(str(current))
    if note.status == "stale" or here != note.base_hash:
        if note.status != "stale":
            note.status = "stale"
            await ctx.db.commit()
        raise note_stale()
    assert current is not None and note.line_start is not None  # guaranteed by `add`
    changed = apply_replacement(
        str(current), note.line_start, note.line_end or note.line_start, note.replacement or ""
    )
    files = {**session.files, str(note.file_path): changed}
    if sum(len(text.encode()) for text in map(str, files.values())) > MAX_TOTAL_BYTES:
        raise files_too_large()
    if not await sessions.claim_files(ctx, session):
        raise note_stale()
    session.files = files
    note.status = "accepted"
    await ctx.db.flush()
    await sweep_stale(ctx, session)
    return session


async def reject(ctx: IdeContext, note_id: str) -> IdeNote:
    """Rejects an open or stale proposal (nothing is written to the files)."""
    _gesture_of_january(ctx)
    note = await get(ctx, note_id)
    if note.kind != "proposal":
        raise not_a_proposal()
    if note.status == "accepted":
        raise note_closed()
    note.status = "rejected"
    await ctx.db.flush()
    return note
