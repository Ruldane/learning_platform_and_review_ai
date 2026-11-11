"""Chaîne d'ingestion d'un document (4.3) : extraction → nettoyage → élément `document` →
fragments → vecteurs. Exécutée par le worker (`jobs.py`), un document à la fois.

Transactions courtes (D66, étapes en base dans `ingest_steps.py`) : (1) le document passe
`processing` ; (2) extraction, sans base ; (3) élément et fragments écrits et validés ;
(4) vectorisation, sans transaction ouverte (le verrou d'écriture de SQLite n'est jamais tenu
pendant l'appel à Ollama) ; (5) statut final. Une reprise rejoue tout : l'élément du document est
retrouvé (mis à jour si le contenu a changé), ses fragments remplacés et tous ses vecteurs
retirés avant réinsertion, donc rien n'est en double.

Les journaux ne citent que des identifiants, des codes et des types d'exception."""

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
FAILED = {"code": "ingestion_failed", "message": "L'import a échoué de façon inattendue."}


async def ingest(runtime: MemoryRuntime, user_id: str, document_id: str) -> None:
    """Importe le document ; toute erreur finit dans son statut (`error`), jamais en exception,
    sauf l'annulation (arrêt du serveur, délai du worker), qui le laisse `processing`, et un
    statut final impossible à écrire malgré les nouveaux essais (le worker le journalise)."""
    claimed = await claim(runtime, user_id, document_id)
    if claimed is None:
        return
    try:
        await _run(runtime, claimed)
    except Gone:
        logger.info("Document %s supprimé pendant son import", document_id)
    except AppError as exc:
        await mark_error(runtime, user_id, document_id, error_of(exc))
    except Exception as exc:
        logger.warning("Import du document %s en échec (%s)", document_id, type(exc).__name__)
        await mark_error(runtime, user_id, document_id, FAILED)


async def _run(runtime: MemoryRuntime, claimed: Claim) -> None:
    providers = runtime.providers
    tools = ExtractionTools(providers.storage, providers.pdf, providers.web, providers.youtube)
    extracted = await get_source(claimed.kind).extract(claimed.source, tools)
    text = clean_text(extracted.text)[: pdf_limits.MAX_TEXT_CHARS]
    if len("".join(text.split())) < MIN_USEFUL_CHARS:
        raise AppError("no_text", "Aucun texte trouvé dans ce document (PDF scanné ?).", 422)
    title = clean_display(extracted.title) or claimed.source.name
    written = await write_item(runtime, claimed, title, text, extracted.lang)
    failure: AppError | None = None
    if written.chunks is not None:
        try:
            await runtime.indexer.push(claimed.source.user_id, written.item_id, written.chunks)
        except (EmbeddingsUnavailable, VectorStoreUnavailable) as exc:
            failure = exc
    await finish(runtime, claimed, written, title, failure)
