"""The user's search settings, read by the settings service (contract 2: search depends only on
the `settings` feature's service, never on its schemas)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.service import SettingsService


@dataclass(frozen=True)
class ResearchPrefs:
    languages: tuple[str, ...]
    preferred: tuple[str, ...]
    excluded: tuple[str, ...]
    provider_order: tuple[str, ...]
    max_queries: int
    max_pages: int


async def load_prefs(db: AsyncSession, user_id: str) -> ResearchPrefs:
    settings = await SettingsService(db, user_id).get()
    return ResearchPrefs(
        languages=tuple(settings.search_languages),
        preferred=tuple(settings.preferred_domains),
        excluded=tuple(settings.excluded_domains),
        provider_order=tuple(settings.search_provider_order),
        max_queries=settings.search_max_queries,
        max_pages=settings.search_max_pages,
    )
