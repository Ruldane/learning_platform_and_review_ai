"""Council board states (SPEC 3.3: "each state is saved", "edits sent back to the agents").
The Scribe writes through the port (upsert by session and step); January edits a scene, saved as
a new state, and her note goes to the Council as a message.

Logs: identifiers only, never a note or a label (SPEC 17.2)."""

import builtins
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.payloads import BoardKind
from app.core.errors import AppError
from app.features.learning.repository import BoardRepository, scribe_key
from app.features.learning.schemas import BoardEdit, BoardOut
from app.features.learning.service.design_boards import append_design_edit
from app.features.learning.service.goals import open_council, owned_goal
from app.features.sessions.service import MessageRequest, SessionsService

logger = logging.getLogger(__name__)

NOTE_PREFIX = "[Board] "


def board_not_found() -> AppError:
    return AppError("board_not_found", "Board state not found.", 404)


async def save_board(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    goal_id: str,
    *,
    step: int,
    kind: BoardKind,
    title: str,
    mermaid: str,
) -> str:
    """Scribe state, upsert by `(session, step)`: on replay, the last write wins (the database
    stays aligned with the latest `board.update`, D85 §11) and the id does not change."""
    await owned_goal(db, user_id, goal_id)
    repo = BoardRepository(db, user_id)
    key = scribe_key(session_id, step)
    row = await repo.by_scribe_key(key)
    if row is None:
        row = await repo.add(
            goal_id=goal_id,
            session_id=session_id,
            step=step,
            kind=kind,
            title=title,
            mermaid=mermaid,
            author="scribe",
            scribe_key=key,
        )
    else:
        row.kind, row.title, row.mermaid = kind, title, mermaid
        await db.flush()
    return row.id


async def list_boards(db: AsyncSession, user_id: str, goal_id: str) -> builtins.list[BoardOut]:
    await owned_goal(db, user_id, goal_id)
    rows = await BoardRepository(db, user_id).list_for_goal(goal_id)
    return [BoardOut.model_validate(row) for row in rows]


async def save_edit(
    db: AsyncSession, runtime: AgentRuntime, user_id: str, board_id: str, edit: BoardEdit
) -> BoardOut:
    """New "user" state (`parent_id` = the edited state), committed before the message; open
    Council → `user.message` "[Board] {note}", read on the next turn; closed Council (or one that
    closes in the meantime) → state kept, no message."""
    repo = BoardRepository(db, user_id)
    parent = await repo.get(board_id)
    if parent is None:
        edited = await append_design_edit(db, user_id, board_id, edit.scene)
        if edited is not None:
            await db.commit()
            return edited
        raise board_not_found()
    row = await repo.add(
        goal_id=parent.goal_id,
        session_id=parent.session_id,
        step=parent.step,
        kind=parent.kind,
        title=parent.title,
        mermaid=parent.mermaid,
        scene=edit.scene,
        author="user",
        parent_id=parent.id,
    )
    out = BoardOut.model_validate(row)
    await db.commit()  # the bus writes in its own session: nothing must hold the database
    council = await open_council(db, user_id, parent.goal_id)
    if council is not None:
        try:
            message = MessageRequest(text=NOTE_PREFIX + edit.note)
            await SessionsService(db, user_id, runtime).message(council, message)
        except AppError as exc:
            if exc.status_code != 409:
                raise
            council = None  # closed between the read and the send: the state stays saved
    logger.info(
        "Board edited: user %s, goal %s, state %s, Council %s",
        user_id,
        parent.goal_id,
        row.id,
        council,
    )
    return out
