"""Release notes already collected by the stack and its WebFetcher."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reading_stack.repository import ReadingRepository


@dataclass(frozen=True)
class CollectedRelease:
    title: str
    text: str
    url: str


async def collected_releases(db: AsyncSession, user_id: str) -> list[CollectedRelease]:
    rows = await ReadingRepository(db, user_id).items(kind="release")
    ordered = sorted(rows, key=lambda row: (row.created_at, row.url))
    return [CollectedRelease(row.title, row.text or row.summary, row.url) for row in ordered]
