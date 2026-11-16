"""La demande du marché (P9, D160) : la part de chaque compétence dans le dernier relevé `done`,
lue par la carte de compétences. Ce module n'importe ni `skills` ni rien qui l'importe
(`radar/service/__init__.py` reste vide) : `skills.map` l'appelle, jamais l'inverse."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.radar.repository import RadarRunRepository


async def latest_demand(db: AsyncSession, user_id: str) -> dict[str, float]:
    """`nom normalisé → part (0 à 1)` des offres analysées du dernier relevé `done` ; vide sans
    relevé fini ou sans offre analysée (la carte dit alors « pas de relevé »)."""
    run = await RadarRunRepository(db, user_id).latest_done()
    if run is None:
        return {}
    return {str(item["norm"]): float(item["share"]) for item in run.ranking}
