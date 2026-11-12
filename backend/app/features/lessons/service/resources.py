"""Ressources des leçons (SPEC 3.6, D91) : 3 à 6 par module, choisies par l'Éclaireur parmi les
sources notées 60 ou plus de la session ; auteur, date et langue viennent de la ligne `sources`,
jamais du modèle. Bibliothèque filtrable par programme, type, langue et statut ; la copie locale
d'un PDF libre n'est servie qu'à son propriétaire."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_port import ResourcePick
from app.core.errors import AppError
from app.db.models.lessons import Resource
from app.db.models.research import Source
from app.features.lessons.repository import ResourceFilter, ResourceRepository
from app.features.lessons.schemas import ResourceOut, ResourcePatch
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


def resource_not_found() -> AppError:
    return AppError("resource_not_found", "Ressource introuvable.", 404)


def resource_file_missing() -> AppError:
    return AppError(
        "resource_file_missing", "Aucune copie locale pour cette ressource : ouvre son lien.", 404
    )


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
    """Le choix du modèle (type, durée, niveau, raison) et la source telle qu'elle a été lue."""
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
) -> int:
    """Ressources du module, une par adresse (`url_hash` de la source) : rejoué, rien ne double.
    Un choix qui ne désigne pas une page retenue de la session est ignoré."""
    repo = ResourceRepository(db, user_id)
    kept = 0
    for pick in picks:
        source = sources.get(pick.source_id)
        if source is None or source.kind != "page" or source.verdict != "kept":
            continue
        fields = _fields(pick, source)
        row = await repo.by_url(module_id, source.url_hash)
        if row is None:
            await repo.add(
                module_id=module_id, program_id=program_id, url_hash=source.url_hash, **fields
            )
        else:
            for key, value in fields.items():
                setattr(row, key, value)
        kept += 1
    await db.flush()
    return kept


async def list_resources(db: AsyncSession, user_id: str, f: ResourceFilter) -> list[ResourceOut]:
    return [to_out(row) for row in await ResourceRepository(db, user_id).filtered(f)]


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
    """La copie locale du PDF, à son propriétaire seulement (ressource d'un autre : 404)."""
    row = await ResourceRepository(db, user_id).get(resource_id)
    if row is None:
        raise resource_not_found()
    if row.local_key is None:
        raise resource_file_missing()
    try:
        return await storage.read(user_id, row.local_key)
    except (FileNotFoundError, StorageKeyInvalid):
        raise resource_file_missing() from None
