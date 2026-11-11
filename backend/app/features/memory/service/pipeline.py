"""Chaîne d'ingestion d'un document (4.3) : extraction → nettoyage → élément `document` →
fragments → vecteurs. Exécutée par le worker (`jobs.py`), un document à la fois.

Transactions courtes (D66) : (1) le document passe `processing` ; (2) extraction, sans base ;
(3) élément et fragments écrits et validés ; (4) vectorisation, sans transaction ouverte (le
verrou d'écriture de SQLite n'est jamais tenu pendant l'appel à Ollama) ; (5) statut final.
Une reprise après arrêt rejoue tout : l'élément est retrouvé par son hash, ses fragments sont
remplacés et tous ses vecteurs retirés avant réinsertion, donc rien n'est en double.

Les journaux ne citent que des identifiants, des codes et des types d'exception."""

import logging
from dataclasses import dataclass
from typing import Any

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.memory import USER_AUTHOR
from app.features.memory.repository import DocumentRepository, MemoryItemRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.sources.base import Extracted, ExtractionTools, SourceInput
from app.features.memory.service.sources.registry import get_source
from app.features.memory.service.text import DISPLAY_NAME_MAX, clean_text
from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.pdf import base as pdf_limits
from app.providers.vector.base import ChunkToIndex, VectorStoreUnavailable

logger = logging.getLogger(__name__)

MIN_USEFUL_CHARS = 20
RESUMABLE = ("queued", "processing")
FAILED = {"code": "ingestion_failed", "message": "L'import a échoué de façon inattendue."}
_RENAMED_BY_TITLE = ("url", "youtube")


@dataclass(frozen=True)
class _Claim:
    source: SourceInput
    kind: str


@dataclass(frozen=True)
class _Written:
    item_id: str
    chunks: list[ChunkToIndex] | None  # None : déjà indexé, rien à pousser


class _Gone(Exception):
    """Le document a disparu pendant l'import (supprimé avec son élément)."""


def error_of(exc: AppError) -> dict[str, Any]:
    """`{code, message}` d'une erreur métier (messages constants, sans contenu reçu) ; l'élément
    existant d'un doublon est gardé (`item_id`)."""
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details and "item_id" in exc.details:
        error["item_id"] = exc.details["item_id"]
    return error


async def ingest(runtime: MemoryRuntime, user_id: str, document_id: str) -> None:
    """Importe le document ; toute erreur finit dans son statut (`error`), jamais en exception,
    sauf l'annulation (arrêt du serveur, délai du worker), qui le laisse `processing`."""
    claim = await _claim(runtime, user_id, document_id)
    if claim is None:
        return
    try:
        await _run(runtime, claim)
    except _Gone:
        logger.info("Document %s supprimé pendant son import", document_id)
    except AppError as exc:
        await mark_error(runtime, user_id, document_id, error_of(exc))
    except Exception as exc:
        logger.warning("Import du document %s en échec (%s)", document_id, type(exc).__name__)
        await mark_error(runtime, user_id, document_id, FAILED)


async def mark_error(
    runtime: MemoryRuntime, user_id: str, document_id: str, error: dict[str, Any]
) -> None:
    """Statut `error` pour un document encore en file ou en cours (sinon rien)."""
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.status not in RESUMABLE:
            return
        doc.status, doc.error = "error", error
        await db.commit()
    logger.info("Document %s en erreur (%s)", document_id, error["code"])


async def _claim(runtime: MemoryRuntime, user_id: str, document_id: str) -> _Claim | None:
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, user_id).get(document_id)
        if doc is None or doc.status not in RESUMABLE:
            return None
        doc.status = "processing"
        await db.commit()
        source = SourceInput(doc.id, user_id, doc.name, doc.url, doc.storage_key)
        return _Claim(source, doc.source_kind)


async def _run(runtime: MemoryRuntime, claim: _Claim) -> None:
    providers = runtime.providers
    tools = ExtractionTools(providers.storage, providers.pdf, providers.web, providers.youtube)
    extracted = await get_source(claim.kind).extract(claim.source, tools)
    text = clean_text(extracted.text)[: pdf_limits.MAX_TEXT_CHARS]
    if len("".join(text.split())) < MIN_USEFUL_CHARS:
        raise AppError("no_text", "Aucun texte trouvé dans ce document (PDF scanné ?).", 422)
    written = await _write(runtime, claim, extracted, text)
    failure: AppError | None = None
    if written.chunks is not None:
        try:
            await runtime.indexer.push(claim.source.user_id, written.item_id, written.chunks)
        except (EmbeddingsUnavailable, VectorStoreUnavailable) as exc:
            failure = exc
    await _finish(runtime, claim, written, extracted.title, failure)


async def _write(
    runtime: MemoryRuntime, claim: _Claim, extracted: Extracted, text: str
) -> _Written:
    """Élément `document` et ses fragments, validés avant toute vectorisation. Le verrou
    d'écriture est pris d'abord : un document supprimé entre-temps arrête l'import."""
    src = claim.source
    async with runtime.session_factory() as db:
        items = MemoryItemRepository(db, src.user_id)
        await items.begin_write()
        if await DocumentRepository(db, src.user_id).get(src.document_id) is None:
            raise _Gone()
        draft = WriteDraft(
            kind="document",
            title=extracted.title,
            text=text,
            author=USER_AUTHOR,
            reason=f"Import du document « {src.name} ».",
            source_id=src.document_id,
            lang=extracted.lang,
        )
        outcome = await MemoryService(db, src.user_id, runtime).write(draft, index=False)
        item = outcome.item
        if not outcome.created and item.source_id != src.document_id:
            raise AppError(
                "duplicate_content",
                f"Ce contenu est déjà en mémoire (« {item.title} »).",
                409,
                details={"item_id": item.id},
            )
        chunks = None
        if outcome.created or item.indexed_at is None:
            chunks = await runtime.indexer.prepare(db, item)
        await DocumentRepository(db, src.user_id).update(src.document_id, item_id=item.id)
        await db.commit()
        return _Written(item.id, chunks)


async def _finish(
    runtime: MemoryRuntime,
    claim: _Claim,
    written: _Written,
    title: str,
    failure: AppError | None,
) -> None:
    """Statut final : `indexed`, ou `error` avec le message du fournisseur en panne (l'élément
    est gardé non indexé : la réindexation le rattrapera)."""
    src = claim.source
    async with runtime.session_factory() as db:
        doc = await DocumentRepository(db, src.user_id).get(src.document_id)
        items = MemoryItemRepository(db, src.user_id)
        item = await items.get(written.item_id)
        if doc is None or item is None:
            return  # supprimés entre-temps (la suppression de l'élément emporte le document)
        if failure is None and written.chunks is not None:
            await items.set_indexed_at(item, utcnow())
        if claim.kind in _RENAMED_BY_TITLE and title.strip():
            doc.name = " ".join(title.split())[:DISPLAY_NAME_MAX]
        doc.item_id = written.item_id
        if failure is None:
            doc.status, doc.error = "indexed", None
        else:
            doc.status, doc.error = "error", error_of(failure)
        await db.commit()
    if failure is None:
        logger.info("Document %s indexé (élément %s)", src.document_id, written.item_id)
    else:
        logger.info("Document %s en erreur (%s)", src.document_id, failure.code)
