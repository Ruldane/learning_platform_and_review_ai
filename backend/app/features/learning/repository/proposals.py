import builtins
from collections.abc import Collection

from sqlalchemy import func, select, update

from app.db.models.learning import Proposal
from app.db.repository import UserScopedRepository


class ProposalRepository(UserScopedRepository[Proposal]):
    """Propositions du Conseil, par lot (`batch`) et par rang. Lectures fraîches
    (`populate_existing`), comme `GoalRepository`."""

    model = Proposal

    async def get_fresh(self, proposal_id: str) -> Proposal | None:
        stmt = (
            select(Proposal)
            .where(Proposal.id == proposal_id, Proposal.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def goal_of(self, proposal_id: str) -> str | None:
        stmt = select(Proposal.goal_id).where(
            Proposal.id == proposal_id, Proposal.user_id == self.user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_batch(self, goal_id: str) -> tuple[str, int] | None:
        """`(session, lot)` du dernier lot de l'objectif, `None` s'il n'y en a aucun."""
        stmt = (
            select(Proposal.session_id, func.max(Proposal.batch))
            .where(Proposal.user_id == self.user_id, Proposal.goal_id == goal_id)
            .group_by(Proposal.session_id)
            .order_by(func.max(Proposal.created_at).desc())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).first()
        return None if row is None else (row[0], int(row[1]))

    async def batch(self, session_id: str, batch: int) -> builtins.list[Proposal]:
        stmt = (
            select(Proposal)
            .where(
                Proposal.user_id == self.user_id,
                Proposal.session_id == session_id,
                Proposal.batch == batch,
            )
            .order_by(Proposal.rank)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def set_chosen(self, session_id: str, batch: int, chosen: Collection[str]) -> None:
        """Marque exactement `chosen` dans le lot (les autres propositions du lot ne le sont
        plus)."""
        stmt = (
            update(Proposal)
            .where(
                Proposal.user_id == self.user_id,
                Proposal.session_id == session_id,
                Proposal.batch == batch,
            )
            .values(chosen=Proposal.id.in_(builtins.list(chosen)))
            .execution_options(synchronize_session=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()
