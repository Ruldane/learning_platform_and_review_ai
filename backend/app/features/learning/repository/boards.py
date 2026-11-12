import builtins

from sqlalchemy import literal_column, select

from app.db.models.learning import Board
from app.db.repository import UserScopedRepository


def scribe_key(session_id: str, step: int) -> str:
    """Clé d'un état du Scribe (« session:step ») : unique par utilisateur (D83)."""
    return f"{session_id}:{step}"


class BoardRepository(UserScopedRepository[Board]):
    """États du tableau d'un utilisateur : ceux du Scribe (clé `scribe_key`) et les retouches de
    January (`author` « user », `parent_id`)."""

    model = Board

    async def by_scribe_key(self, key: str) -> Board | None:
        stmt = (
            select(Board)
            .where(Board.user_id == self.user_id, Board.scribe_key == key)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_goal(self, goal_id: str) -> builtins.list[Board]:
        """Tous les états de l'objectif dans l'ordre où ils ont été créés."""
        stmt = (
            select(Board)
            .where(Board.user_id == self.user_id, Board.goal_id == goal_id)
            .order_by(Board.created_at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
