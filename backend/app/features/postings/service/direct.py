"""A posting written directly (phase 10, 10.W): January or Claude (through MCP) gives the
posting text and its analysis (title, company, requirements, keywords, skills...), the
application stores them as the Analyst's port does (`save_analysis`), without an agent, a
session or a model call: the posting is "ready" at once, with its `posting` memory item
(indexed) and its probable and possible duplicates. The skills gap, however, is launched as
before (`POST /postings/{id}/gap`): it is an agent, it is not launched here.

Duplicates as for `POST /postings` (same link, or same text without a link: existing posting,
200; link never read). A failed or refused posting receives the given analysis. Written through
the ORM only: the MCP history sees every row and the undo removes it."""

import logging

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.posting_schema import (
    PostingAnalysis,
    enough_text,
    keyword_problems,
    requirement_problems,
)
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.memory.service.direct import author_of, schedule_indexing, write_direct
from app.features.memory.service.upload import normalize_url
from app.features.postings.repository import PostingRepository
from app.features.postings.schemas import (
    TEXT_MAX,
    URL_MAX,
    PostingCreatedOut,
    PostingDirectIn,
    PostingOut,
    PostingPatch,
)
from app.features.postings.service.agent_store import item_title, not_analyzed
from app.features.postings.service.create import (
    Source,
    posting_too_short,
    text_digest,
)
from app.features.postings.service.duplicates import (
    find_duplicates,
    not_found,
    prefetch_scores,
    store_duplicates,
)
from app.features.postings.service.queries import read_posting
from app.features.postings.service.rules import company_key, posting_url_key
from app.features.postings.service.runtime import PostingsRuntime

logger = logging.getLogger(__name__)

TITLE_MAX = 200
MEMORY_REASON = "Saved the text of a posting entered directly."


def posting_analysis_invalid(fields: list[str]) -> AppError:
    """422: the analysis fields to fix, never their value."""
    return AppError(
        "posting_analysis_invalid",
        "A keyword does not appear in the posting, or a required skill is missing from `skills`.",
        422,
        {"fields": fields},
    )


def _invalid_url() -> AppError:
    return AppError("invalid_url", "Invalid posting link.", 422, {"fields": ["url"]})


def _analysis(data: dict[str, object], text: str) -> PostingAnalysis:
    """The validated analysis; its keywords and requirements are checked against the text (422)."""
    try:
        analysis = PostingAnalysis.model_validate({**data, "is_job_posting": True})
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
        raise AppError(
            "validation_error",
            "Invalid request. Check the highlighted fields.",
            422,
            {"fields": fields or ["body"]},
        ) from None
    if fields := _problems(analysis, text):
        raise posting_analysis_invalid(fields)
    return analysis


def _source(url: str | None, text: str) -> Source:
    """The normalized link (never read) or, without a link, the text itself as the source."""
    if url is None or not url.strip():
        return Source(None, None, text)
    try:
        normalized, key = normalize_url(url), posting_url_key(url)
    except AppError as exc:
        if exc.code in ("invalid_url", "url_forbidden"):
            raise AppError(exc.code, exc.message, 422, {"fields": ["url"]}) from None
        raise
    if len(normalized) > URL_MAX or len(key) > URL_MAX:
        raise _invalid_url()
    return Source(normalized, key, None)


def _apply(posting: JobPosting, analysis: PostingAnalysis) -> None:
    company = (analysis.company or "").strip() or None
    posting.analysis = analysis.model_dump(mode="json")
    posting.title = analysis.title[:TITLE_MAX]
    posting.company = company[:TITLE_MAX] if company else None
    posting.company_norm = (company_key(company) or None) if company else None
    posting.status, posting.failure_reason = "ready", None


async def _existing(
    rt: PostingsRuntime, user_id: str, source: Source, text: str
) -> JobPosting | None:
    async with rt.session_factory() as db:
        repo = PostingRepository(db, user_id)
        if source.url_norm is not None:
            return await repo.by_url_norm(source.url_norm)
        return await repo.by_text_hash(text_digest(text))


def _problems(analysis: PostingAnalysis, text: str) -> list[str]:
    """The analysis fields that the text or the `skills` list does not support."""
    fields = []
    if keyword_problems(analysis, text):
        fields.append("keywords")
    if requirement_problems(analysis):
        fields.append("requirements")
    return fields


async def _memory_and_duplicates(
    db: AsyncSession,
    rt: PostingsRuntime,
    user_id: str,
    posting: JobPosting,
    analysis: PostingAnalysis,
    *,
    scores: dict[str, float],
    is_mcp: bool,
    replaces_title: str | None = None,
) -> None:
    """In the posting's transaction: its `posting` memory item (written or updated, not indexed
    here: see `memory.service.direct`), then its probable and possible duplicates, stored on
    both sides; those that no longer hold are removed from the other side. `scores`: the search
    for close postings, already done (`_scores`): no network wait here, under the write
    lock."""
    item_id = await write_direct(
        db,
        rt.memory,
        user_id,
        kind="posting",
        title=item_title(analysis),
        text=posting.text,
        tags=("posting",),
        author=author_of(is_mcp),
        reason=MEMORY_REASON,
        replaces=None if replaces_title is None else (replaces_title, posting.text),
    )
    if posting.memory_item_id is None:
        posting.memory_item_id = item_id
    await db.flush()
    hits = await find_duplicates(db, rt.memory, user_id, posting, scores)
    gone = {str(d.get("posting_id")) for d in posting.duplicates if isinstance(d, dict)}
    gone -= {hit.posting_id for hit in hits}
    for other in (await PostingRepository(db, user_id).by_ids(gone)).values():
        other.duplicates = [d for d in other.duplicates if d.get("posting_id") != posting.id]
    await store_duplicates(db, user_id, posting, hits)


async def _scores(
    db: AsyncSession,
    rt: PostingsRuntime,
    user_id: str,
    analysis: PostingAnalysis,
    text: str,
    row: JobPosting | None,
) -> dict[str, float]:
    """The search for close postings (embedding and Qdrant, sometimes several seconds when
    Ollama is cold), done **before the first write**: SQLite's write lock never waits for the
    network (D66). `row`: the posting already there (resume or edit), `None` for a new one."""
    company = (analysis.company or "").strip() or None
    return await prefetch_scores(
        db,
        rt.memory,
        user_id,
        title=analysis.title[:TITLE_MAX],
        company=company[:TITLE_MAX] if company else None,
        text=text,
        own_id=None if row is None else row.id,
        own_item_id=None if row is None else row.memory_item_id,
        distinct_from=[] if row is None else list(row.distinct_from or []),
    )


async def _store(
    rt: PostingsRuntime,
    user_id: str,
    source: Source,
    text: str,
    analysis: PostingAnalysis,
    *,
    is_mcp: bool,
) -> tuple[str, bool] | None:
    """`(id, created)`: the posting written at once with its analysis, its memory and its
    duplicates, in one transaction (new, or resuming a posting whose analysis had failed);
    `None` if the posting already exists and has nothing to receive."""
    async with rt.session_factory() as db:
        found = await _existing(rt, user_id, source, text)
        created = found is None
        if found is not None:
            if found.analysis is not None or found.status not in ("failed", "rejected"):
                return None
            if fields := _problems(analysis, found.text):  # the posting keeps its original text
                raise posting_analysis_invalid(fields)
            row = await PostingRepository(db, user_id).get_fresh(found.id)
            assert row is not None
            scores = await _scores(db, rt, user_id, analysis, row.text, row)
        else:
            scores = await _scores(db, rt, user_id, analysis, text, None)
            row = JobPosting(
                user_id=user_id,
                url=source.url,
                url_norm=source.url_norm,
                source="url" if source.url_norm else "text",
                text=text,
                text_hash=text_digest(text),
            )
            db.add(row)
        _apply(row, analysis)
        try:
            await db.flush()
            await _memory_and_duplicates(
                db, rt, user_id, row, analysis, scores=scores, is_mcp=is_mcp
            )
            await db.commit()
        except IntegrityError:  # another request has just written it: we return its own
            await db.rollback()
            return None
        return row.id, created


async def create_direct(
    rt: PostingsRuntime, user_id: str, body: PostingDirectIn, *, is_mcp: bool
) -> PostingCreatedOut:
    """See the module. 422 `posting_too_short`, `invalid_url`, `url_forbidden`,
    `posting_analysis_invalid`: never the input in the response."""
    text = body.text.strip()
    if not enough_text(text):
        raise posting_too_short()
    analysis = _analysis(body.model_dump(exclude={"text", "url"}), text)
    source = _source(body.url, text)
    async with rt.source_locks.get(user_id, source.key):
        stored = await _store(rt, user_id, source, text, analysis, is_mcp=is_mcp)
        if stored is None:
            existing = await _existing(rt, user_id, source, text)
            if existing is None:
                raise RuntimeError("winning posting not found after a uniqueness conflict")
            posting_id, created = existing.id, False
        else:
            posting_id, created = stored
            schedule_indexing(rt.memory, user_id)
    logger.info(
        "Posting written directly: user %s, posting %s, created %s", user_id, posting_id, created
    )
    async with rt.session_factory() as db:
        posting = await read_posting(db, user_id, posting_id)
    return PostingCreatedOut(posting=posting, created=created, session_id=None)


async def patch_direct(
    rt: PostingsRuntime, user_id: str, posting_id: str, patch: PostingPatch, *, is_mcp: bool
) -> PostingOut:
    """Edits the analysis of an analyzed posting (409 `posting_not_analyzed` otherwise, 404 if it
    is not mine): title, company, level, requirements...; its memory item and its duplicates
    are recomputed."""
    changes = patch.model_dump(exclude_none=True)
    async with rt.source_locks.get(user_id, f"posting:{posting_id}"):
        async with rt.session_factory() as db:
            posting = await PostingRepository(db, user_id).get_fresh(posting_id)
            if posting is None:
                raise not_found()
            if posting.analysis is None:
                raise not_analyzed()
            before = item_title(PostingAnalysis.model_validate(posting.analysis))
            analysis = _analysis({**posting.analysis, **changes}, posting.text[:TEXT_MAX])
            scores = await _scores(db, rt, user_id, analysis, posting.text, posting)
            _apply(posting, analysis)
            await _memory_and_duplicates(
                db, rt, user_id, posting, analysis, scores=scores, is_mcp=is_mcp,
                replaces_title=before,
            )  # fmt: skip
            await db.commit()
        schedule_indexing(rt.memory, user_id)
    logger.info("Posting edited directly: user %s, posting %s", user_id, posting_id)
    async with rt.session_factory() as db:
        return await read_posting(db, user_id, posting_id)
