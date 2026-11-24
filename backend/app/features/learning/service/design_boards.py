"""States of an Excalidraw exercise, independent of a Council goal."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import MCP_IDENTITY
from app.core.errors import AppError
from app.db.models.learning import DesignBoardVersion
from app.features.learning.repository.design_boards import DesignBoards
from app.features.learning.schemas import BoardOut as BoardOut


def _out(row: DesignBoardVersion) -> BoardOut:
    return BoardOut(
        id=row.id,
        goal_id=None,
        session_id=row.session_id,
        step=row.step,
        kind="system_design",
        title="Architecture diagram",
        mermaid="",
        scene=row.scene,
        author="user",
        parent_id=row.parent_id,
        created_at=row.created_at,
    )


async def create_design_board(
    db: AsyncSession, user_id: str, interview_id: str, session_id: str
) -> None:
    await DesignBoards(db, user_id).add(
        interview_id=interview_id,
        session_id=session_id,
        scene={"elements": [], "files": {}},
        step=0,
    )


async def read_design_board(
    db: AsyncSession, user_id: str, interview_id: str, board_id: str | None = None
) -> BoardOut:
    repo = DesignBoards(db, user_id)
    row = await (repo.get(board_id) if board_id else repo.latest(interview_id))
    if row is None or row.interview_id != interview_id:
        raise AppError("board_not_found", "Board state not found.", 404)
    return _out(row)


async def append_design_edit(
    db: AsyncSession, user_id: str, board_id: str, scene: dict[str, Any]
) -> BoardOut | None:
    if MCP_IDENTITY.get() is not None:
        return None
    repo = DesignBoards(db, user_id)
    parent = await repo.lock(board_id)
    if parent is None:
        return None
    elements = scene.get("elements")
    if not isinstance(elements, list) or not all(isinstance(item, dict) for item in elements):
        raise AppError("board_scene_invalid", "The Excalidraw scene is invalid.", 422)
    newest = await repo.latest(parent.interview_id)
    row = await repo.add(
        interview_id=parent.interview_id,
        session_id=parent.session_id,
        parent_id=parent.id,
        step=(newest.step if newest is not None else parent.step) + 1,
        scene=scene,
    )
    return _out(row)
