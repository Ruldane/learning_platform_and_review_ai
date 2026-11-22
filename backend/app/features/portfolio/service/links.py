from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.portfolio_urls import public_url
from app.features.portfolio.repository import Sites


async def approved_link(
    db: AsyncSession,
    user_id: str,
    target: Literal["cv", "kit"],
    origin: str | None,
) -> str | None:
    if origin is None:
        return None
    row = await Sites(db, user_id).for_owner()
    if row is None or not row.published_id or row.published_url != public_url(origin, row.slug):
        return None
    enabled = row.use_in_cv if target == "cv" else row.use_in_kit
    return row.published_url if enabled else None
