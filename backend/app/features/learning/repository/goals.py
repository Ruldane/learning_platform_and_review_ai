import builtins

from sqlalchemy import literal_column, select

from app.db.models.learning import Goal
from app.db.models.program import Program
from app.db.repository import UserScopedRepository


class GoalRepository(UserScopedRepository[Goal]):
    """Objectifs d'un utilisateur. Les lectures rafraîchissent les lignes déjà chargées
    (`populate_existing`) : sous le verrou d'un objectif, une requête voit l'état commité par la
    précédente, pas une copie gardée par la session."""

    model = Goal

    async def get_fresh(self, goal_id: str) -> Goal | None:
        stmt = (
            select(Goal)
            .where(Goal.id == goal_id, Goal.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent(self) -> builtins.list[Goal]:
        stmt = (
            select(Goal)
            .where(Goal.user_id == self.user_id)
            .order_by(Goal.created_at.desc(), literal_column("rowid").desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def latest_program(self, goal_id: str) -> tuple[str, str | None] | None:
        """Le programme le plus récent de l'objectif : `(id, session program_builder)`."""
        stmt = (
            select(Program.id, Program.session_id)
            .where(Program.user_id == self.user_id, Program.goal_id == goal_id)
            .order_by(Program.created_at.desc(), literal_column("rowid").desc())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).first()
        return None if row is None else (row[0], row[1])
