"""Lectures et suppression des offres (SPEC 14.2, D122) : liste (plus récentes d'abord), détail
(texte figé, analyse, doublons relus, statut montré), suppression avec l'élément de mémoire
`offre` (revues et versions en cascade ; 409 si une revue tourne). Journaux : identifiants
seulement."""

import logging
from collections.abc import Sequence
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
from app.features.postings.service.status import read_with_sessions, shown_status

logger = logging.getLogger(__name__)


def review_in_progress() -> AppError:
    return AppError(
        "review_in_progress", "Une revue de CV de cette offre est en cours : attends sa fin.", 409
    )


async def get_posting(db: AsyncSession, user_id: str, posting_id: str) -> JobPosting:
    """L'offre de January, relue ; 404 `posting_not_found` sinon."""
    posting = await PostingRepository(db, user_id).get_fresh(posting_id)
    if posting is None:
        raise not_found()
    return posting


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


async def delete_posting(
    db: AsyncSession, memory: MemoryRuntime, user_id: str, posting_id: str
) -> None:
    """Supprime l'offre (revues et versions en cascade) et son élément de mémoire `offre`, sauf
    s'il sert encore à une autre offre (même texte). **Valide la transaction.**"""
    repo = PostingRepository(db, user_id)
    posting = await get_posting(db, user_id, posting_id)
    if await repo.running_reviews(posting_id):
        raise review_in_progress()
    item_id = posting.memory_item_id
    shared = item_id is not None and await repo.item_shared(item_id, posting_id)
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
    logger.info("Offre supprimée : utilisateur %s, offre %s", user_id, posting_id)
