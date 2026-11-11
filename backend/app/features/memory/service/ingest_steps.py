"""Étapes en base de la chaîne d'ingestion (`pipeline.py`), chacune une transaction courte.

Les écritures de fin (`finish`, `mark_error`) sont rejouées deux fois au plus si SQLite refuse
le verrou d'écriture (« database is locked » après les 5 s de `busy_timeout`) : un statut final
perdu laisserait le document `processing` jusqu'au prochain démarrage."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.memory import USER_AUTHOR, Document, MemoryItem
from app.features.memory.repository import (
    DocumentRepository,
    MemoryItemRepository,
    WriteRepository,
)
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.sources.base import SourceInput
from app.features.memory.service.text import clean_display, content_hash
from app.providers.vector.base import ChunkToIndex, VectorStoreUnavailable

logger = logging.getLogger(__name__)

RESUMABLE = ("queued", "processing")
RETRIES = 2
RETRY_BACKOFF_S = 0.2
_RENAMED_BY_TITLE = ("url", "youtube")


@dataclass(frozen=True)
class Claim:
    source: SourceInput
    kind: str


@dataclass(frozen=True)
class Written:
    item_id: str
    chunks: list[ChunkToIndex] | None  # None : déjà indexé, rien à pousser


class Gone(Exception):
    """Le document a disparu pendant l'import (supprimé avec son élément)."""


def error_of(exc: AppError) -> dict[str, Any]:
    """`{code, message}` d'une erreur métier (messages constants, sans contenu reçu) ; l'élément
    existant d'un doublon est gardé (`item_id`)."""
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details and "item_id" in exc.details:
        error["item_id"] = exc.details["item_id"]
    return error


def duplicate_content(item_id: str) -> AppError:
    return AppError(
        "duplicate_content", "Ce contenu est déjà en mémoire.", 409, details={"item_id": item_id}
    )


async def with_retry[**P](
    step: Callable[P, Awaitable[None]], *args: P.args, **kwargs: P.kwargs
) -> None:
    for attempt in range(RETRIES + 1):
        try:
            await step(*args, **kwargs)
            return
        except OperationalError as exc:
            if attempt == RETRIES:
                raise
            logger.warning("Écriture refusée par SQLite (%s), nouvel essai", type(exc).__name__)
            await asyncio.sleep(RETRY_BACKOFF_S * (attempt + 1))


async def claim(runtime: MemoryRuntime, user_id: str, document_id: str) -> Claim | None:
    """Le document passe `processing` ; `None` s'il est introuvable ou déjà traité."""
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.status not in RESUMABLE:
            return None
        doc.status = "processing"
        await db.commit()
        return Claim(
            SourceInput(doc.id, user_id, doc.name, doc.url, doc.storage_key), doc.source_kind
        )


async def write_item(
    runtime: MemoryRuntime, claim: Claim, title: str, text: str, lang: str | None
) -> Written:
    """Élément `document` et ses fragments, validés avant toute vectorisation. Le verrou
    d'écriture est pris d'abord : un document supprimé entre-temps arrête l'import. Le document
    a déjà son élément (reprise, nouvelle lecture d'un lien) : cet élément est mis à jour, jamais
    doublé."""
    src = claim.source
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, src.user_id)
        await items.begin_write()
        if await DocumentRepository(db, src.user_id).get(src.document_id) is None:
            raise Gone()
        own = await items.find_document_of(src.document_id)
        if own is None:
            item, changed = await _create(db, runtime, src, title, text, lang)
        else:
            item, changed = await _refresh(db, src, own, title, text, lang)
        chunks = None
        if changed or item.indexed_at is None:
            chunks = await runtime.indexer.prepare(db, item)
        await DocumentRepository(db, src.user_id).update(src.document_id, item_id=item.id)
        await db.commit()
        return Written(item.id, chunks)


async def _create(
    db: AsyncSession,
    runtime: MemoryRuntime,
    src: SourceInput,
    title: str,
    text: str,
    lang: str | None,
) -> tuple[MemoryItem, bool]:
    draft = WriteDraft(
        kind="document",
        title=title,
        text=text,
        author=USER_AUTHOR,
        reason=f"Import du document « {src.name} ».",
        source_id=src.document_id,
        lang=lang,
    )
    outcome = await MemoryService(db, src.user_id, runtime).write(draft, index=False)
    if not outcome.created and outcome.item.source_id != src.document_id:
        raise duplicate_content(outcome.item.id)
    return outcome.item, outcome.created


async def _refresh(
    db: AsyncSession, src: SourceInput, own: MemoryItem, title: str, text: str, lang: str | None
) -> tuple[MemoryItem, bool]:
    """Nouveau contenu pour l'élément du document (page modifiée entre deux lectures). Le
    verrou d'écriture est tenu : aucune insertion concurrente du même hash n'est possible."""
    digest = content_hash("document", title, text)
    if digest == own.content_hash:
        return own, False
    clash = await MemoryItemRepository(db, src.user_id).find_by_hash(digest)
    if clash is not None:
        raise duplicate_content(clash.id)
    own.title, own.text, own.content_hash, own.lang = title, text, digest, lang
    await db.flush()
    await WriteRepository(db, src.user_id).log(
        item=own,
        action="update",
        author=USER_AUTHOR,
        session_id=None,
        reason=f"Nouvelle lecture du document « {src.name} ».",
    )
    return own, True


async def finish_once(
    runtime: MemoryRuntime, claim: Claim, written: Written, title: str, failure: AppError | None
) -> None:
    """Statut final : `indexed`, ou `error` avec le message du fournisseur en panne (l'élément
    est gardé non indexé : la réindexation le rattrapera). Le verrou d'écriture est pris avant
    les lectures : le document et l'élément ne peuvent plus disparaître avant le commit. Élément
    supprimé pendant le `push` : les vecteurs poussés après sa suppression sont retirés une
    fois la transaction close (M2, D71). Document seul disparu (l'élément reste) : rien n'est
    retiré, l'élément déjà marqué non indexé par `prepare` sera rattrapé par la réindexation."""
    src = claim.source
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, src.user_id)
        await items.begin_write()
        doc = await DocumentRepository(db, src.user_id).get(src.document_id)
        item = await items.get(written.item_id)
        if doc is None or item is None:
            await db.rollback()  # supprimés entre-temps (l'élément emporte le document)
        else:
            await _settle(items, doc, item, claim, written, title, failure)
            await db.commit()
    if item is None and written.chunks is not None:
        await drop_orphan_vectors(runtime, src.user_id, written.item_id)
    if doc is None or item is None:
        return
    if failure is None:
        logger.info("Document %s indexé (élément %s)", src.document_id, written.item_id)
    else:
        logger.info("Document %s en erreur (%s)", src.document_id, failure.code)


async def _settle(
    items: MemoryItemRepository,
    doc: Document,
    item: MemoryItem,
    claim: Claim,
    written: Written,
    title: str,
    failure: AppError | None,
) -> None:
    if failure is None and written.chunks is not None:
        # Conditionnel (D67) : des fragments renouvelés entre-temps (modification pendant le
        # `push`) laissent l'élément à rattraper au lieu de le dire indexé à tort.
        first = written.chunks[0].chunk_id if written.chunks else None
        await items.mark_indexed(item, utcnow(), first)
    if claim.kind in _RENAMED_BY_TITLE and clean_display(title):
        doc.name = clean_display(title)  # titre venu du site : nettoyé comme un nom reçu
    doc.item_id = written.item_id
    if failure is None:
        doc.status, doc.error = "indexed", None
    else:
        doc.status, doc.error = "error", error_of(failure)


async def drop_orphan_vectors(runtime: MemoryRuntime, user_id: str, item_id: str) -> None:
    """Retire les vecteurs d'un élément supprimé pendant son import, hors de toute transaction ;
    une panne du magasin est avalée et journalisée par identifiant (la réindexation purge les
    orphelins restants, la recherche les écarte déjà)."""
    try:
        await runtime.providers.index.delete_items(user_id, [item_id])
    except VectorStoreUnavailable:
        logger.warning(
            "Vecteurs orphelins de l'élément %s non retirés : magasin indisponible", item_id
        )
        return
    logger.info("Vecteurs orphelins de l'élément %s retirés (supprimé pendant l'import)", item_id)


async def finish(
    runtime: MemoryRuntime, claim: Claim, written: Written, title: str, failure: AppError | None
) -> None:
    await with_retry(finish_once, runtime, claim, written, title, failure)


async def mark_error_once(
    runtime: MemoryRuntime, user_id: str, document_id: str, error: dict[str, Any]
) -> None:
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.status not in RESUMABLE:
            return
        doc.status, doc.error = "error", error
        await db.commit()
    logger.info("Document %s en erreur (%s)", document_id, error["code"])


async def mark_error(
    runtime: MemoryRuntime, user_id: str, document_id: str, error: dict[str, Any]
) -> None:
    """Statut `error` pour un document encore en file ou en cours (sinon rien)."""
    await with_retry(mark_error_once, runtime, user_id, document_id, error)
