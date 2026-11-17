"""Le rapport des coûts d'une utilisatrice : ses appels journalisés, aux prix de l'appel, sur
les `days` derniers jours de son fuseau."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment, local_today, user_zone
from app.features.costs.repository import LlmCallRepository
from app.features.costs.schemas import CostsReport
from app.features.costs.service.rules import CallFact, aggregate, window
from app.features.settings.service import SettingsService


async def costs_report(
    db: AsyncSession, user_id: str, days: int, now: datetime | None = None
) -> CostsReport:
    """Le rapport des `days` derniers jours locaux, aujourd'hui compris (`now` : pour les tests)."""
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    since, until = window(local_today(zone, now), days)
    rows = await LlmCallRepository(db, user_id).since(local_moment(since, "00:00", zone))
    facts = [
        CallFact(
            at=row.created_at,
            graph=row.graph,
            agent=row.agent,
            provider=row.provider,
            model=row.model,
            tokens_in=row.tokens_in,
            tokens_out=row.tokens_out,
            cost_usd=row.cost_usd,
            estimated=row.estimated,
        )
        for row in rows
    ]
    return aggregate(facts, zone, since, until)
