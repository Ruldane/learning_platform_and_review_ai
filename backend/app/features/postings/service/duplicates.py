"""Duplicates of a posting (SPEC F8, 14.2, D122). The "certain" level (same link, same text) is
the 200 response of `POST /postings`. The "probable" and "possible" levels need the company
and the title: they are computed after the analysis (`save_analysis`, G35):
- probable: same company (`company_key`) and close titles (`PROBABLE_TITLE`);
- possible: same company, and the other posting's `posting` memory item has a close chunk
  (`POSSIBLE_COSINE`) among the first 5 search results;
- "distinct postings" (`distinct_from`, on both sides) removes them; never the posting itself.

Stored on both postings (`duplicates`: level, posting, score), re-read for display: a deleted
posting disappears, title, company and date are those of the other posting. Dates are returned
in January's time zone. Logs: ids and numbers only."""

import logging
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.gap_port import DuplicateHit, DuplicateLevel
from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.repository import PostingRepository
from app.features.postings.service.rules import (
    POSSIBLE_COSINE,
    PROBABLE_TITLE,
    company_key,
    title_similarity,
)
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

SEARCH_HITS = 5
QUERY_MAX = 500  # `SearchRequest.query`


async def zone_of(db: AsyncSession, user_id: str) -> ZoneInfo:
    return user_zone((await SettingsService(db, user_id).get()).timezone)


def _hit(
    level: DuplicateLevel, other: JobPosting, zone: ZoneInfo, score: float | None
) -> DuplicateHit:
    created = other.created_at.astimezone(zone).isoformat()
    return DuplicateHit(level, other.id, other.title, other.company, created, score)


def _apart(posting: JobPosting, other: JobPosting) -> bool:
    """ "Distinct postings", said on one side or the other."""
    return other.id in posting.distinct_from or posting.id in other.distinct_from


def search_query(posting: JobPosting) -> str:
    return query_of(posting.title, posting.company, posting.text)


def query_of(title: str | None, company: str | None, text: str) -> str:
    head = " ".join(part for part in (title, company) if part)
    return f"{head}\n{text}".strip()[:QUERY_MAX]


async def _best_scores(
    memory: MemoryRuntime, user_id: str, query: str, own_item_id: str | None, label: str | None
) -> dict[str, float]:
    """`memory item → best score` of the close postings; search unavailable: none (the possible
    duplicate is only a signal)."""
    gateway = AgentMemoryGateway(memory)
    try:
        found = await gateway.search(user_id, query, kinds=["posting"], k=SEARCH_HITS + 1)
    except AppError as exc:
        logger.warning("Possible duplicates not searched: posting %s (%s)", label, exc.code)
        return {}
    best: dict[str, float] = {}
    for hit in found.hits:
        if hit.item_id == own_item_id:
            continue
        if hit.item_id in best or len(best) < SEARCH_HITS:
            best[hit.item_id] = max(best.get(hit.item_id, 0.0), hit.score)
    return best


async def prefetch_scores(
    db: AsyncSession,
    memory: MemoryRuntime,
    user_id: str,
    *,
    title: str,
    company: str | None,
    text: str,
    own_id: str | None,
    own_item_id: str | None,
    distinct_from: list[Any],
) -> dict[str, float]:
    """The search scores that `find_duplicates` will need for the described posting, computed
    **before any write**: vectorization (Ollama) and search (Qdrant) can take several seconds,
    and SQLite's write lock must not wait for them (D66). `{}` without a company or without
    another posting of the same company that is not already "probable" (no search in that case).
    `db` must not have written any row yet."""
    norm = company_key(company) if company else ""
    if not norm:
        return {}
    others = await PostingRepository(db, user_id).same_company(norm, own_id or "")
    rest = [
        other
        for other in others
        if other.memory_item_id
        and other.id not in distinct_from
        and (own_id is None or own_id not in other.distinct_from)
        and title_similarity(title, other.title or "") < PROBABLE_TITLE
    ]
    if not rest:
        return {}
    return await _best_scores(
        memory, user_id, query_of(title, company, text), own_item_id, "written"
    )


async def find_duplicates(
    db: AsyncSession,
    memory: MemoryRuntime,
    user_id: str,
    posting: JobPosting,
    scores: dict[str, float] | None = None,
) -> list[DuplicateHit]:
    """The probable then possible duplicates of the analyzed posting, oldest first. `scores`:
    those that `prefetch_scores` has already searched (no network wait here); otherwise the
    search is done here."""
    if not posting.company_norm:
        return []
    same = [
        other
        for other in await PostingRepository(db, user_id).same_company(
            posting.company_norm, posting.id
        )
        if not _apart(posting, other)
    ]
    if not same:
        return []
    zone = await zone_of(db, user_id)
    title = posting.title or ""
    probable = [o for o in same if title_similarity(title, o.title or "") >= PROBABLE_TITLE]
    hits: list[DuplicateHit] = [_hit("probable", other, zone, None) for other in probable]
    rest = [o for o in same if o not in probable and o.memory_item_id]
    if rest and posting.memory_item_id:
        found = (
            scores
            if scores is not None
            else await _best_scores(
                memory, user_id, search_query(posting), posting.memory_item_id, posting.id
            )
        )
        for other in rest:
            score = found.get(other.memory_item_id or "")
            if score is not None and score >= POSSIBLE_COSINE:
                hits.append(_hit("possible", other, zone, round(score, 4)))
    return hits


def _stored(level: str, posting_id: str, score: float | None) -> dict[str, Any]:
    return {"level": level, "posting_id": posting_id, "score": score}


async def store_duplicates(
    db: AsyncSession, user_id: str, posting: JobPosting, hits: list[DuplicateHit]
) -> None:
    """Stores the duplicates on the posting and, reciprocally, on each other posting (without a
    duplicate row). The commit belongs to the caller."""
    posting.duplicates = [_stored(h.level, h.posting_id, h.score) for h in hits]
    others = await PostingRepository(db, user_id).by_ids([h.posting_id for h in hits])
    for hit in hits:
        other = others.get(hit.posting_id)
        if other is None or any(d.get("posting_id") == posting.id for d in other.duplicates):
            continue
        other.duplicates = [*other.duplicates, _stored(hit.level, posting.id, hit.score)]
    await db.flush()


async def shown_duplicates(
    db: AsyncSession, user_id: str, posting: JobPosting, zone: ZoneInfo
) -> list[DuplicateHit]:
    """The stored duplicates, re-read: postings still there and not declared distinct."""
    stored = [d for d in posting.duplicates if isinstance(d, dict) and d.get("posting_id")]
    others = await PostingRepository(db, user_id).by_ids([str(d["posting_id"]) for d in stored])
    hits: list[DuplicateHit] = []
    for item in stored:
        other = others.get(str(item["posting_id"]))
        level = item.get("level")
        if other is None or _apart(posting, other) or level not in ("probable", "possible"):
            continue
        score = item.get("score")
        hits.append(_hit(level, other, zone, float(score) if score is not None else None))
    return hits


def not_found() -> AppError:
    return AppError("posting_not_found", "Posting not found.", 404)


async def mark_distinct(db: AsyncSession, user_id: str, posting_id: str, other_id: str) -> None:
    """ "Distinct postings": each excludes the other and the duplicate disappears on both sides.
    Idempotent; an absent posting (or another user's): 404. The commit belongs to the caller."""
    found = await PostingRepository(db, user_id).by_ids({posting_id, other_id})
    if posting_id == other_id or len(found) != 2:  # noqa: PLR2004
        raise not_found()
    for one, two in ((posting_id, other_id), (other_id, posting_id)):
        row = found[one]
        if two not in row.distinct_from:
            row.distinct_from = [*row.distinct_from, two]
        row.duplicates = [d for d in row.duplicates if d.get("posting_id") != two]
    await db.flush()
    logger.info("Distinct postings: user %s, postings %s and %s", user_id, posting_id, other_id)
