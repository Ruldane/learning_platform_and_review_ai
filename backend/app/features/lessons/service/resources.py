"""Lesson resources (SPEC 3.6, D91): 3 to 6 per module, chosen by the Scout among the session's
sources scored 60 or more; author, date and language come from the `sources` row, never from the
model. Library filterable by program, type, language and status; the local copy of a free PDF is
only served to its owner."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_port import ResourcePick
from app.core.errors import AppError
from app.db.models.lessons import Resource
from app.db.models.research import Source
from app.features.lessons.repository import ResourceFilter, ResourceRepository
from app.features.lessons.schemas import ResourceOut, ResourcePatch, ResourceWriteIn
from app.features.research.service.cache import url_key
from app.providers.storage.base import FileStorage, StorageKeyInvalid

__all__ = [
    "ResourceFilter",
    "list_resources",
    "patch_resource",
    "resource_file",
    "to_out",
    "upsert_resources",
]

_MAX_LANG = 8
_MAX_DATE = 32
_MAX_REASON = 300
READING_NOTE_MAX = 2000


def resource_not_found() -> AppError:
    return AppError("resource_not_found", "Resource not found.", 404)


def resource_file_missing() -> AppError:
    return AppError("resource_file_missing", "No local copy for this resource: open its link.", 404)


def to_out(row: Resource) -> ResourceOut:
    return ResourceOut.model_validate(
        {
            "id": row.id,
            "module_id": row.module_id,
            "program_id": row.program_id,
            "type": row.type,
            "title": row.title,
            "url": row.url,
            "author": row.author,
            "date": row.published,
            "lang": row.lang,
            "duration_minutes": row.duration_minutes,
            "level": row.level,
            "reason": row.reason,
            "score": row.score,
            "status": row.status,
            "has_local_copy": row.local_key is not None,
            "note": row.note,
        }
    )


def _cut(value: str | None, size: int) -> str | None:
    return value[:size] if value else None


def _fields(pick: ResourcePick, source: Source) -> dict[str, object]:
    """The model's choice (type, duration, level, reason) and the source as it was read."""
    return {
        "source_id": source.id,
        "type": pick.type,
        "title": (source.title or source.url).strip() or source.url,
        "url": source.url,
        "author": source.author,
        "published": _cut(source.published, _MAX_DATE),
        "lang": _cut(source.lang, _MAX_LANG),
        "duration_minutes": pick.duration_minutes,
        "level": pick.level,
        "reason": pick.reason[:_MAX_REASON],
        "score": source.score,
    }


async def upsert_resources(
    db: AsyncSession,
    user_id: str,
    *,
    module_id: str,
    program_id: str,
    picks: Sequence[ResourcePick],
    sources: dict[str, Source],
    preserve_existing: bool = False,
) -> int:
    """The module's resources, one per address (the source's `url_hash`): replayed, nothing is
    duplicated. A pick that does not point to a kept page of the session is ignored."""
    repo = ResourceRepository(db, user_id)
    kept = 0
    for pick in picks:
        source = sources.get(pick.source_id)
        if source is None or source.kind != "page" or source.verdict != "kept":
            continue
        fields = _fields(pick, source)
        row = await repo.by_url(module_id, source.url_hash)
        if row is None:
            if preserve_existing:
                text = (source.summary or source.reason or "Note unavailable.").strip()
                fields["note"] = text[:READING_NOTE_MAX]
            await repo.add(
                module_id=module_id, program_id=program_id, url_hash=source.url_hash, **fields
            )
        elif not preserve_existing:
            for key, value in fields.items():
                setattr(row, key, value)
        kept += 1
    await db.flush()
    return kept


async def attach_resources(
    db: AsyncSession,
    user_id: str,
    *,
    module_id: str,
    program_id: str,
    readings: Sequence[ResourceWriteIn],
) -> None:
    """Adds the links in the lesson's transaction, without touching notes already read."""
    if not readings:
        return
    repo = ResourceRepository(db, user_id)
    for reading in readings:
        key = url_key(str(reading.url))
        if await repo.by_url(module_id, key) is not None:
            continue
        fields = reading.model_dump(mode="json", exclude={"date"}, exclude_none=True)
        await repo.add(
            module_id=module_id,
            program_id=program_id,
            url_hash=key,
            published=reading.date,
            **fields,
        )


async def list_resources(db: AsyncSession, user_id: str, f: ResourceFilter) -> list[ResourceOut]:
    return [to_out(row) for row in await ResourceRepository(db, user_id).filtered(f)]


async def repository_resources(
    db: AsyncSession, user_id: str, program_id: str
) -> tuple[tuple[str, str], ...]:
    """Links of studied repositories, with their module, for contribution suggestions."""
    filter_ = ResourceFilter(program_id=program_id, type="repository")
    rows = await ResourceRepository(db, user_id).filtered(filter_)
    return tuple((row.module_id, row.url) for row in rows)


async def patch_resource(
    db: AsyncSession, user_id: str, resource_id: str, patch: ResourcePatch
) -> ResourceOut:
    row = await ResourceRepository(db, user_id).update(resource_id, status=patch.status)
    if row is None:
        raise resource_not_found()
    return to_out(row)


async def resource_file(
    db: AsyncSession, storage: FileStorage, user_id: str, resource_id: str
) -> bytes:
    """The local copy of the PDF, to its owner only (someone else's resource: 404)."""
    row = await ResourceRepository(db, user_id).get(resource_id)
    if row is None:
        raise resource_not_found()
    if row.local_key is None:
        raise resource_file_missing()
    try:
        return await storage.read(user_id, row.local_key)
    except (FileNotFoundError, StorageKeyInvalid):
        raise resource_file_missing() from None
