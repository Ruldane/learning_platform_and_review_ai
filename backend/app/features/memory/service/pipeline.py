"""Ingestion chain of a document (4.3): extraction → cleaning → `document` item →
chunks → vectors. Run by the worker (`jobs.py`), one document at a time.

Short transactions (D66, database steps in `ingest_steps.py`): (1) the document becomes
`processing`; (2) extraction, without the database; (3) item and chunks written and committed;
(4) embedding, with no open transaction (SQLite's write lock is never held during the Ollama
call); (5) final status. A retry replays everything: the document's item is found again
(updated if the content changed), its chunks replaced and all its vectors removed before
reinsertion, so nothing is duplicated.

Logs only mention identifiers, codes and exception types."""

import logging

from app.core.errors import AppError
from app.features.memory.service.ingest_steps import (
    Claim,
    Gone,
    claim,
    error_of,
    finish,
    mark_error,
    write_item,
)
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.sources.base import ExtractionTools
from app.features.memory.service.sources.registry import get_source
from app.features.memory.service.text import clean_display, clean_text
from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.pdf import base as pdf_limits
from app.providers.vector.base import VectorStoreUnavailable

__all__ = ["FAILED", "MIN_USEFUL_CHARS", "error_of", "ingest", "mark_error"]

logger = logging.getLogger(__name__)

MIN_USEFUL_CHARS = 20
FAILED = {"code": "ingestion_failed", "message": "The import failed unexpectedly."}


async def ingest(runtime: MemoryRuntime, user_id: str, document_id: str) -> None:
    """Imports the document; any error ends up in its status (`error`), never as an exception,
    except cancellation (server shutdown, worker timeout), which leaves it `processing`, and a
    final status that cannot be written despite retries (the worker logs it)."""
    claimed = await claim(runtime, user_id, document_id)
    if claimed is None:
        return
    try:
        await _run(runtime, claimed)
    except Gone:
        logger.info("Document %s deleted during its import", document_id)
    except AppError as exc:
        await mark_error(runtime, user_id, document_id, error_of(exc))
    except Exception as exc:
        logger.warning("Import of document %s failed (%s)", document_id, type(exc).__name__)
        await mark_error(runtime, user_id, document_id, FAILED)


async def _run(runtime: MemoryRuntime, claimed: Claim) -> None:
    providers = runtime.providers
    tools = ExtractionTools(providers.storage, providers.pdf, providers.web, providers.youtube)
    extracted = await get_source(claimed.kind).extract(claimed.source, tools)
    text = clean_text(extracted.text)[: pdf_limits.MAX_TEXT_CHARS]
    if len("".join(text.split())) < MIN_USEFUL_CHARS:
        raise AppError("no_text", "No text found in this document (scanned PDF?).", 422)
    title = clean_display(extracted.title) or claimed.source.name
    written = await write_item(runtime, claimed, title, text, extracted.lang)
    failure: AppError | None = None
    if written.chunks is not None:
        try:
            await runtime.indexer.push(claimed.source.user_id, written.item_id, written.chunks)
        except (EmbeddingsUnavailable, VectorStoreUnavailable) as exc:
            failure = exc
    await finish(runtime, claimed, written, title, failure)
