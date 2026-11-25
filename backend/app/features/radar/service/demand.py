"""Market demand (P9, D160): the share of each skill in the last `done` scan, read by the skill
map. This module imports neither `skills` nor anything that imports it (`radar/service/__init__.py`
stays empty): `skills.map` calls it, never the reverse."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.radar.repository import RadarRunRepository


async def latest_demand(db: AsyncSession, user_id: str) -> dict[str, float]:
    """`normalized name → share (0 to 1)` of the analysed offers of the last `done` scan **that
    analysed at least one** (a blind scan does not replace a usable one); empty without such a scan
    (the map then says "no scan")."""
    run = await RadarRunRepository(db, user_id).latest_done(min_analyzed=1)
    if run is None:
        return {}
    return {str(item["norm"]): float(item["share"]) for item in run.ranking}
