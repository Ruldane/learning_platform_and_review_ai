"""Résolution des renvois Obsidian à partir des documents de la mémoire."""

import posixpath
from collections import defaultdict
from collections.abc import Iterable
from unicodedata import normalize

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import MemoryItem
from app.features.memory.repository.linked_notes import NoteCandidate, active_folder_notes
from app.features.memory.schemas import LinkedNoteOut

__all__ = ["NoteCandidate", "NoteLinkIndex", "linked_notes"]


def _key(name: str) -> str:
    return normalize("NFC", name).casefold()


def _file_names(path: str) -> set[str]:
    stem, ext = posixpath.splitext(path)
    return {path, stem} if ext in {".md", ".markdown"} else {path}


def _resolve_path(link: str, origin: str) -> str | None:
    if link.startswith("/"):
        return None
    if link.startswith(("./", "../")):
        link = posixpath.join(posixpath.dirname(origin), link)
    path = posixpath.normpath(link)
    return None if path in {".", ".."} or path.startswith("../") else _key(path)


def _index_candidates(
    candidates: list[NoteCandidate],
) -> tuple[dict[str, set[NoteCandidate]], dict[str, set[NoteCandidate]]]:
    names: dict[str, set[NoteCandidate]] = defaultdict(set)
    paths: dict[str, set[NoteCandidate]] = defaultdict(set)
    for note in candidates:
        path = _key(note.path)
        for name in _file_names(posixpath.basename(path)) | {_key(note.title)}:
            names[name].add(note)
        for name in _file_names(path):
            paths[name].add(note)
    return names, paths


class NoteLinkIndex:
    """Un index par dossier, réutilisable pour chaque note du dossier."""

    def __init__(self, candidates: list[NoteCandidate]) -> None:
        self._names, self._paths = _index_candidates(candidates)

    def _matches(self, link: str, path: str) -> set[NoteCandidate] | None:
        if "/" in link:
            key = _resolve_path(link, path)
            return self._paths.get(key) if key is not None else None
        return self._names.get(_key(link))

    def targets(self, origin: NoteCandidate, links: Iterable[object]) -> list[NoteCandidate]:
        found: dict[str, NoteCandidate] = {}
        for link in links:
            if not isinstance(link, str):
                continue
            matches = self._matches(link, origin.path)
            if matches and len(matches) == 1:
                (note,) = matches
                if note.item_id != origin.item_id:
                    found[note.item_id] = note
        return list(found.values())


async def linked_notes(db: AsyncSession, item: MemoryItem) -> list[LinkedNoteOut]:
    meta = (item.meta or {}).get("sync_metadata")
    links = meta.get("links") if isinstance(meta, dict) else None
    if not isinstance(links, list) or not links:
        return []
    candidates = await active_folder_notes(db, item.user_id, item.id)
    origin = next((note for note in candidates if note.item_id == item.id), None)
    if origin is None:
        return []
    return [
        LinkedNoteOut(item_id=note.item_id, title=note.title)
        for note in NoteLinkIndex(candidates).targets(origin, links)
    ]
