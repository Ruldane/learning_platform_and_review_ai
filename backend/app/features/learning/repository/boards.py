import builtins

from sqlalchemy import literal_column, select

from app.db.models.learning import Board
from app.db.repository import UserScopedRepository


def scribe_key(session_id: str, step: int) -> str:
    """Key of a Scribe state ("session:step"): unique per user (D83)."""
    return f"{session_id}:{step}"


class BoardRepository(UserScopedRepository[Board]):
    """A user's board states: the Scribe's (key `scribe_key`) and January's edits
    (`author` "user", `parent_id`)."""

    model = Board

    async def by_scribe_key(self, key: str) -> Board | None:
        stmt = (
            select(Board)
            .where(Board.user_id == self.user_id, Board.scribe_key == key)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_goal(self, goal_id: str) -> builtins.list[Board]:
        """All the goal's states, in creation order."""
        stmt = (
            select(Board)
            .where(Board.user_id == self.user_id, Board.goal_id == goal_id)
            .order_by(Board.created_at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
