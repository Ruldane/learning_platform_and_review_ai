from collections.abc import Collection, Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.brain.reading_repository import NoteReadingRepository

MAX_NOTES = 5
MAX_MATERIAL = 1_600


@dataclass(frozen=True)
class ActiveNote:
    item_id: str
    title: str
    version: str
    material: str


async def active_note_versions(
    db: AsyncSession, user_id: str, item_ids: Collection[str]
) -> dict[str, str]:
    return await NoteReadingRepository(db, user_id).versions(item_ids)


async def matching_notes(db: AsyncSession, user_id: str, terms: Sequence[str]) -> list[ActiveNote]:
    if not terms:
        return []
    found = await NoteReadingRepository(db, user_id).matching(terms, MAX_NOTES)
    return [
        ActiveNote(item_id, title, version, text[:MAX_MATERIAL])
        for item_id, title, version, text in found
    ]
