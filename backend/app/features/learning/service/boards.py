"""États du tableau du Conseil (SPEC 3.3 : « chaque état est enregistré », « modifications renvoyées
aux agents »). Le Scribe écrit par le port (upsert par session et étape) ; January retouche une
scène, enregistrée comme un nouvel état, et sa note part au Conseil comme un message.

Journaux : identifiants seulement, jamais une note ni un libellé (SPEC 17.2)."""

import builtins
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.payloads import BoardKind
from app.core.errors import AppError
from app.features.learning.repository import BoardRepository, scribe_key
from app.features.learning.schemas import BoardEdit, BoardOut
from app.features.learning.service.goals import open_council, owned_goal
from app.features.sessions.service import MessageRequest, SessionsService

logger = logging.getLogger(__name__)

NOTE_PREFIX = "[Tableau] "


def board_not_found() -> AppError:
    return AppError("board_not_found", "État du tableau introuvable.", 404)


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
    """État du Scribe, upsert par `(session, étape)` : rejoué, le dernier écrit gagne (la base
    reste alignée sur le dernier `board.update`, D85 §11) et l'id ne change pas."""
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
    """Nouvel état « user » (`parent_id` = l'état retouché), commité avant le message ; Conseil
    ouvert → `user.message` « [Tableau] {note} », lu au tour suivant ; Conseil clos (ou qui se
    ferme entre-temps) → état gardé, aucun message."""
    repo = BoardRepository(db, user_id)
    parent = await repo.get(board_id)
    if parent is None:
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
    await db.commit()  # le bus écrit dans sa propre session : rien ne doit tenir la base
    council = await open_council(db, user_id, parent.goal_id)
    if council is not None:
        try:
            message = MessageRequest(text=NOTE_PREFIX + edit.note)
            await SessionsService(db, user_id, runtime).message(council, message)
        except AppError as exc:
            if exc.status_code != 409:
                raise
            council = None  # fermé entre la lecture et l'envoi : l'état reste enregistré
    logger.info(
        "Tableau retouché : utilisateur %s, objectif %s, état %s, Conseil %s",
        user_id,
        parent.goal_id,
        row.id,
        council,
    )
    return out
