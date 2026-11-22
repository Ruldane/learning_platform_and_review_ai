"""Graphe des documents actifs du synchroniseur, sans chemin ni texte."""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.brain.reading_repository import NoteReadingRepository
from app.features.brain.service.reading import LESSON_REFERENCE
from app.features.memory.service.linked_notes import NoteCandidate, NoteLinkIndex


@dataclass(frozen=True)
class SyncedNote:
    id: str
    title: str
    linked_ids: tuple[str, ...]
    lesson_ids: tuple[str, ...]
    tags: tuple[str, ...]


def _strings(value: object) -> tuple[str, ...]:
    return tuple(v for v in value if isinstance(v, str)) if isinstance(value, list) else ()


async def synced_note_graph(db: AsyncSession, user_id: str) -> list[SyncedNote]:
    folders: dict[str, list[tuple[NoteCandidate, tuple[str, ...], tuple[str, ...]]]] = defaultdict(
        list
    )
    for folder, path, item_id, title, metadata in await NoteReadingRepository(
        db, user_id
    ).link_entries():
        info = metadata or {}
        folders[folder].append(
            (
                NoteCandidate(path, item_id, title),
                _strings(info.get("links")),
                _strings(info.get("tags")),
            )
        )
    notes: list[SyncedNote] = []
    for entries in folders.values():
        index = NoteLinkIndex([note for note, _, _ in entries])
        for note, links, tags in entries:
            notes.append(
                SyncedNote(
                    note.item_id,
                    note.title,
                    tuple(target.item_id for target in index.targets(note, links)),
                    tuple(
                        link.removeprefix(LESSON_REFERENCE)
                        for link in links
                        if link.startswith(LESSON_REFERENCE)
                    ),
                    tags,
                )
            )
    return sorted(notes, key=lambda note: (note.title.casefold(), note.id))
