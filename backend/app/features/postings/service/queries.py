"""Lectures et suppression des offres (SPEC 14.2, D122) : liste (plus récentes d'abord), détail
(texte figé, analyse, doublons relus, statut montré), suppression avec l'élément de mémoire
`offre` (revues et versions en cascade, puis leurs fichiers ; 409 `review_in_progress` si une revue
de CV tourne ou attend, 409 `analysis_in_progress` si l'analyse de l'offre est ouverte, 409
`posting_has_application` tant qu'une fiche de candidature la cite). Journaux :
identifiants seulement."""

import asyncio
import logging
from collections.abc import Collection, Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.gap.service.rows import rows_by_posting
from app.features.gap.service.score import GapRow, match_score
from app.features.memory.service.items import MemoryService
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.repository import PostingRepository
from app.features.postings.schemas import (
    DuplicateOut,
    PostingAnalysisOut,
    PostingOut,
    PostingSummaryOut,
)
from app.features.postings.service.duplicates import not_found, shown_duplicates, zone_of
from app.features.postings.service.status import open_sessions, read_with_sessions, shown_status

logger = logging.getLogger(__name__)


def review_in_progress() -> AppError:
    return AppError(
        "review_in_progress", "Une revue de CV de cette offre est en cours : attends sa fin.", 409
    )


def posting_has_application(application_id: str) -> AppError:
    return AppError(
        "posting_has_application",
        "Une candidature cite cette offre : elle ne peut pas être supprimée.",
        409,
        {"application_id": application_id},
    )


def analysis_in_progress() -> AppError:
    return AppError(
        "analysis_in_progress",
        "Une analyse de cette offre est en cours : réessaie dans un instant.",
        409,
    )


async def get_posting(db: AsyncSession, user_id: str, posting_id: str) -> JobPosting:
    """L'offre de January, relue ; 404 `posting_not_found` sinon."""
    posting = await PostingRepository(db, user_id).get_fresh(posting_id)
    if posting is None:
        raise not_found()
    return posting


async def postings_by_ids(
    db: AsyncSession, user_id: str, posting_ids: Collection[str]
) -> dict[str, JobPosting]:
    """Les offres de January parmi `posting_ids` (lecture seule, pour les candidatures) ; une
    offre absente n'y figure pas."""
    return await PostingRepository(db, user_id).by_ids(posting_ids)


def _score(rows: Sequence[GapRow] | None) -> int | None:
    return None if rows is None else match_score(rows)


def summary_out(
    posting: JobPosting, open_ids: list[str], rows: Sequence[GapRow] | None, reviewed: bool
) -> PostingSummaryOut:
    status, _ = shown_status(posting, open_ids)
    return PostingSummaryOut.model_validate(
        {
            "id": posting.id,
            "title": posting.title,
            "company": posting.company,
            "status": status,
            "source": posting.source,
            "score": _score(rows),
            "created_at": posting.created_at,
            "has_review": reviewed,
        }
    )


async def posting_out(
    db: AsyncSession, user_id: str, posting: JobPosting, open_ids: list[str]
) -> PostingOut:
    rows = (await rows_by_posting(db, user_id, [posting])).get(posting.id)
    reviewed = posting.id in await PostingRepository(db, user_id).reviewed([posting.id])
    summary = summary_out(posting, open_ids, rows, reviewed)
    hits = await shown_duplicates(db, user_id, posting, await zone_of(db, user_id))
    analysis = (
        PostingAnalysisOut.model_validate(posting.analysis)
        if posting.analysis is not None
        else None
    )
    return PostingOut(
        **summary.model_dump(),
        url=posting.url,
        text=posting.text,
        analysis=analysis,
        duplicates=[
            DuplicateOut(
                level=hit.level,
                posting_id=hit.posting_id,
                title=hit.title,
                company=hit.company,
                created_at=datetime.fromisoformat(hit.created_at),
            )
            for hit in hits
        ],
        failure_reason=shown_status(posting, open_ids)[1],
        gap_session_id=posting.gap_session_id,
    )


async def read_posting(db: AsyncSession, user_id: str, posting_id: str) -> PostingOut:
    async def read() -> JobPosting:
        return await get_posting(db, user_id, posting_id)

    posting, open_ids = await read_with_sessions(db, user_id, read, lambda p: [p])
    return await posting_out(db, user_id, posting, open_ids.get(posting.id, []))


async def list_postings(db: AsyncSession, user_id: str) -> list[PostingSummaryOut]:
    repo = PostingRepository(db, user_id)
    postings, open_ids = await read_with_sessions(db, user_id, repo.list_recent, lambda r: r)
    rows = await rows_by_posting(db, user_id, postings)
    reviewed = await repo.reviewed([p.id for p in postings])
    return [
        summary_out(p, open_ids.get(p.id, []), rows.get(p.id), p.id in reviewed) for p in postings
    ]


async def _erase_files(memory: MemoryRuntime, user_id: str, keys: list[str]) -> None:
    """Retire les PDF et les images des versions, après le commit ; un échec n'est journalisé que
    par son type (la ligne a disparu : le fichier est orphelin, jamais l'inverse)."""
    for key in keys:
        try:
            await memory.providers.storage.delete(user_id, key)
        except Exception as exc:  # noqa: BLE001 - un fichier de moins ne défait pas la suppression
            logger.warning(
                "Fichier de version non retiré : utilisateur %s, %s", user_id, type(exc).__name__
            )


async def delete_posting(
    db: AsyncSession,
    memory: MemoryRuntime,
    review_lock: asyncio.Lock,
    user_id: str,
    posting_id: str,
) -> None:
    """Supprime l'offre (revues et versions en cascade), l'élément de mémoire `offre` (sauf s'il
    sert encore à une autre offre) puis, la transaction validée, les fichiers des versions.
    409 `review_in_progress` (revue lancée ou proposée) ou `analysis_in_progress` (session
    d'analyse ouverte). `review_lock` : le verrou des revues de l'utilisatrice (`CvRuntime`), pris
    avant la vérification et gardé jusqu'au commit : une revue créée entre les deux ne part pas en
    cascade (D137 n° 7). **Valide la transaction.**"""
    async with review_lock:
        files = await _delete_rows(db, memory, user_id, posting_id)
    await _erase_files(memory, user_id, files)
    logger.info("Offre supprimée : utilisateur %s, offre %s", user_id, posting_id)


async def _delete_rows(
    db: AsyncSession, memory: MemoryRuntime, user_id: str, posting_id: str
) -> list[str]:
    """Les vérifications, puis les lignes et l'élément de mémoire, jusqu'au commit ; rend les clés
    des fichiers des versions à retirer."""
    repo = PostingRepository(db, user_id)
    posting = await get_posting(db, user_id, posting_id)
    application_id = await repo.application_id(posting_id)
    if application_id is not None:
        raise posting_has_application(application_id)
    if await repo.running_reviews(posting_id):
        raise review_in_progress()
    if await open_sessions(db, user_id, posting_id):
        raise analysis_in_progress()
    item_id = posting.memory_item_id
    shared = item_id is not None and await repo.item_shared(item_id, posting_id)
    files = await repo.version_files(posting_id)
    await db.delete(posting)
    await db.flush()
    if item_id is not None and not shared:
        try:
            await MemoryService(db, user_id, memory).delete(item_id)  # valide la transaction
        except AppError as exc:
            if exc.code != "memory_item_not_found":
                raise
            await db.commit()  # élément déjà retiré par January
    else:
        await db.commit()
    return files
