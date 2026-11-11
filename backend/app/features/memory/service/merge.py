"""Fusion d'éléments de la mémoire (4.6, D67) : `POST /memory/items/{id}/merge`.

Les autres éléments sont fondus dans la cible : texte (cible puis textes des autres non
identiques, séparés par une ligne vide), étiquettes et preuves réunies dans l'ordre de première
apparition, niveau le plus haut pour un acquis. Les autres sont supprimés (journal `delete`), la
cible est journalisée `merge` puis réindexée. Même schéma que l'écriture (D66) : tout est validé
en base avant d'appeler Qdrant, et `index_item` est la dernière étape."""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError
from app.db.models.memory import MASTERY_ORDER, USER_AUTHOR, MasteryLevel, MemoryItem, MemoryKind
from app.features.memory.repository import MemoryItemRepository, WriteRepository
from app.features.memory.schemas import MemoryItemOut
from app.features.memory.service.items import MemoryService, duplicate, to_out
from app.features.memory.service.rules import clean_tags
from app.features.memory.service.text import content_hash

SEPARATOR = "\n\n"


def _check(target: MemoryItem, others: Sequence[MemoryItem]) -> None:
    everyone = [target, *others]
    if any(item.kind == "document" for item in everyone):
        raise AppError(
            "merge_document_forbidden", "Un document ne se fusionne pas : supprime le doublon.", 409
        )
    if any(item.kind != target.kind for item in others):
        raise AppError("merge_kind_mismatch", "On ne fusionne que des éléments du même type.", 422)
    if any(item.status != "active" for item in everyone):
        raise AppError(
            "merge_pending_forbidden",
            "Confirme ou refuse d'abord la décision en attente avant de la fusionner.",
            409,
        )


def _merged(
    target: MemoryItem, others: Sequence[MemoryItem]
) -> tuple[str, list[str], dict[str, Any]]:
    """Texte, étiquettes et `meta` de la cible après fusion."""
    everyone = [target, *others]
    texts: dict[str, str] = {}  # texte normalisé (casse, espaces) -> texte d'origine
    for item in everyone:
        texts.setdefault(" ".join(item.text.casefold().split()), item.text)
    tags = clean_tags([str(tag) for item in everyone for tag in item.tags])
    evidence = list(
        dict.fromkeys(str(e) for item in everyone for e in (item.meta or {}).get("evidence", []))
    )
    meta = dict(target.meta or {})
    if evidence:
        meta["evidence"] = evidence
    if target.kind == "acquis":
        levels = [
            cast(MasteryLevel, (item.meta or {}).get("level") or "declare") for item in everyone
        ]
        meta["level"] = max(levels, key=MASTERY_ORDER.__getitem__)
    return SEPARATOR.join(texts.values()), tags, meta


async def merge(service: MemoryService, target_id: str, other_ids: Sequence[str]) -> MemoryItemOut:
    """Fond `other_ids` dans `target_id` (même utilisateur : 404 sinon). Refus lisibles : rien à
    fusionner (422), document (409), types différents (422), décision en attente (409), contenu
    fusionné identique à un autre élément (409)."""
    ids = list(dict.fromkeys(i for i in other_ids if i != target_id))
    if not ids:
        raise AppError("merge_nothing", "Choisis au moins un autre élément à fusionner.", 422)
    target = await service.get(target_id)
    others = [await service.get(item_id) for item_id in ids]
    _check(target, others)
    text, tags, meta = _merged(target, others)
    db, user_id = service.db, service.user_id
    items, writes = MemoryItemRepository(db, user_id), WriteRepository(db, user_id)
    await items.begin_write()  # avant le SAVEPOINT (D65 c)
    for other in others:
        reason = f"Fusionné dans « {target.title} »."
        await writes.log(
            item=other, action="delete", author=USER_AUTHOR, session_id=None, reason=reason
        )
        await items.delete(other.id)
    digest = content_hash(cast(MemoryKind, target.kind), target.title, text)
    clash = await items.find_by_hash(digest)
    if clash is not None and clash.id != target.id:
        raise duplicate()
    try:
        async with db.begin_nested():
            target.text, target.tags, target.content_hash, target.meta = text, tags, digest, meta
            await db.flush()
    except IntegrityError:
        raise duplicate() from None
    reason = f"Fusion de {len(others)} élément(s)."
    await writes.log(
        item=target, action="merge", author=USER_AUTHOR, session_id=None, reason=reason
    )
    await db.commit()  # rien n'est tenu pendant les appels à Qdrant qui suivent
    await service.runtime.indexer.unindex(user_id, ids)
    await service.runtime.indexer.index_item(db, target)  # dernière étape (D66)
    return to_out(target)
