"""Reads and deletion of postings (SPEC 14.2, D122): list (most recent first), detail (frozen
text, analysis, re-read duplicates, status shown), deletion with the `posting` memory item
(reviews and versions cascade, then their files; 409 `review_in_progress` if a CV review is
running or waiting, 409 `analysis_in_progress` if the posting's analysis is open, 409
`posting_has_application` as long as an application record cites it, 409
`posting_has_running_work` as long as a committee or an interview in progress cites it).
Logs: ids only."""

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
    return AppError("review_in_progress", "Wait for this posting's CV review to finish.", 409)


def posting_has_application(application_id: str) -> AppError:
    return AppError(
        "posting_has_application",
        "This posting is linked to an application and cannot be deleted.",
        409,
        {"application_id": application_id},
    )


def posting_has_running_work(kind: str) -> AppError:
    return AppError(
        "posting_has_running_work",
        "Wait for the active committee or interview about this posting to finish.",
        409,
        {"kind": kind},
    )


def analysis_in_progress() -> AppError:
    return AppError(
        "analysis_in_progress",
        "This posting is being analyzed. Try again in a moment.",
        409,
    )


async def get_posting(db: AsyncSession, user_id: str, posting_id: str) -> JobPosting:
    """January's posting, re-read; 404 `posting_not_found` otherwise."""
    posting = await PostingRepository(db, user_id).get_fresh(posting_id)
    if posting is None:
        raise not_found()
    return posting


async def postings_by_ids(
    db: AsyncSession, user_id: str, posting_ids: Collection[str]
) -> dict[str, JobPosting]:
    """January's postings among `posting_ids` (read-only, for applications); an absent
    posting is not included."""
    return await PostingRepository(db, user_id).by_ids(posting_ids)


async def postings_for_chat(db: AsyncSession, user_id: str) -> list[JobPosting]:
    """Read the account's saved offers without refreshing or starting analysis."""
    return await PostingRepository(db, user_id).list_recent()


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
    """Removes the PDFs and images of the versions, after the commit; a failure is only logged
    by its type (the row is gone: the file is orphaned, never the reverse)."""
    for key in keys:
        try:
            await memory.providers.storage.delete(user_id, key)
        except Exception as exc:  # noqa: BLE001 - one file less does not undo the deletion
            logger.warning("Version file not removed: user %s, %s", user_id, type(exc).__name__)


async def delete_posting(
    db: AsyncSession,
    memory: MemoryRuntime,
    review_lock: asyncio.Lock,
    user_id: str,
    posting_id: str,
) -> None:
    """Deletes the posting (reviews and versions cascade), the `posting` memory item (unless it
    still serves another posting) then, once the transaction is committed, the version files.
    409 `review_in_progress` (review launched or proposed), `analysis_in_progress` (analysis
    session open) or `posting_has_running_work` (committee or interview in progress,
    `details.kind`). `review_lock`: the user's reviews lock (`CvRuntime`), taken before the
    checks and kept until the commit: a review created between the two does not cascade away
    (D137 no. 7). **Commits the transaction.**"""
    async with review_lock:
        files = await _delete_rows(db, memory, user_id, posting_id)
    await _erase_files(memory, user_id, files)
    logger.info("Posting deleted: user %s, posting %s", user_id, posting_id)


async def _delete_rows(
    db: AsyncSession, memory: MemoryRuntime, user_id: str, posting_id: str
) -> list[str]:
    """The checks, then the rows and the memory item, up to the commit; returns the keys of the
    version files to remove."""
    repo = PostingRepository(db, user_id)
    posting = await get_posting(db, user_id, posting_id)
    application_id = await repo.application_id(posting_id)
    if application_id is not None:
        raise posting_has_application(application_id)
    if await repo.running_reviews(posting_id):
        raise review_in_progress()
    if (running := await repo.running_work(posting_id)) is not None:
        raise posting_has_running_work(running)
    if await open_sessions(db, user_id, posting_id):
        raise analysis_in_progress()
    item_id = posting.memory_item_id
    shared = item_id is not None and await repo.item_shared(item_id, posting_id)
    files = await repo.version_files(posting_id)
    await db.delete(posting)
    await db.flush()
    if item_id is not None and not shared:
        try:
            await MemoryService(db, user_id, memory).delete(item_id)  # commits the transaction
        except AppError as exc:
            if exc.code != "memory_item_not_found":
                raise
            await db.commit()  # item already removed by January
    else:
        await db.commit()
    return files
