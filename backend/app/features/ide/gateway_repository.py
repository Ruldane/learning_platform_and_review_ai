from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.ide_gateway import IdeGatewayBudget


async def reserve(db: AsyncSession, user_id: str, day: str, amount: int, cap: int) -> bool:
    """Réserve d'un coup, y compris sous requêtes concurrentes."""
    if amount > cap:
        return False
    budget = IdeGatewayBudget
    stmt = insert(budget).values(user_id=user_id, day=day, reserved=amount)
    claimed = stmt.on_conflict_do_update(
        index_elements=[budget.user_id, budget.day],
        set_={"reserved": budget.reserved + amount, "updated_at": utcnow()},
        where=budget.reserved + amount <= cap,
    ).returning(budget.id)
    return (await db.execute(claimed)).scalar_one_or_none() is not None
