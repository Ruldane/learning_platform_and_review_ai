"""Adding a posting (SPEC F8, 14.2, D122): `POST /postings` with its link OR its pasted text.

- Link: key `posting_url_key` (tracking parameters removed). Same key already there → the
  existing posting (200, "certain" duplicate). Otherwise the page is read **within the
  request** by the web search (7-day cache, no transaction during the read, D66); unreadable or
  too short (`enough_text`) → 422 `posting_unreadable` asking for the text: no posting guessed.
- Text: too short → 422 `posting_too_short`; sha256 fingerprint of the normalized text; same
  fingerprint already there → the existing posting (200).
- Two simultaneous sends of the same source wait for each other (lock per source); the unique
  index (`uq_job_postings_url`, `uq_job_postings_text`) catches the rest: the loser re-reads
  the winner.
- An existing posting that is refused, failed or interrupted is relaunched rather than
  returned as is.

A 422 never copies the input back (`details.fields` only). Logs: ids only, never the link, the
text or the company (SPEC 17.2)."""

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.agents.tools.posting_schema import enough_text
from app.core.errors import AppError
from app.db.models.postings import JobPosting
from app.features.memory.service.upload import normalize_url
from app.features.postings.repository import PostingRepository
from app.features.postings.schemas import TEXT_MAX, URL_MAX, PostingCreatedOut, PostingIn
from app.features.postings.service.launch import launch_new, relaunch
from app.features.postings.service.queries import read_posting
from app.features.postings.service.rules import posting_url_key, route_fragment
from app.features.postings.service.runtime import PostingsRuntime
from app.features.research.service.reading import read

logger = logging.getLogger(__name__)

_SPACES = re.compile(r"\s+")
_URL_ERRORS = ("invalid_url", "url_forbidden")


def posting_source() -> AppError:
    return AppError(
        "posting_source",
        "Provide either the posting link or its text.",
        422,
        {"fields": ["url", "text"]},
    )


def posting_unreadable() -> AppError:
    return AppError(
        "posting_unreadable",
        "This posting could not be read from its link. Paste the posting text instead.",
        422,
        {"fields": ["url"]},
    )


def posting_too_short() -> AppError:
    return AppError(
        "posting_too_short",
        "Posting text is too short. Paste the full posting.",
        422,
        {"fields": ["text"]},
    )


def _url_error(exc: AppError) -> AppError:
    """`invalid_url` or `url_forbidden`, fixed message, without the received address."""
    return AppError(exc.code, exc.message, 422, {"fields": ["url"]})


def text_digest(text: str) -> str:
    """Fingerprint of a posting text: NFC, whitespace collapsed to one space, edges stripped."""
    normalized = _SPACES.sub(" ", unicodedata.normalize("NFC", text)).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Source:
    url: str | None  # the normalized link (`normalize_url`), read as is
    url_norm: str | None  # the idempotency key (`posting_url_key`)
    text: str | None  # the pasted text; `None` for a link (read afterwards)

    @property
    def key(self) -> str:
        return f"url:{self.url_norm}" if self.url_norm else f"text:{text_digest(self.text or '')}"


def _given(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def source_of(body: PostingIn) -> Source:
    """Exactly one source, checked (see the module)."""
    if _given(body.url) == _given(body.text):
        raise posting_source()
    if body.url is not None and body.url.strip():
        try:
            url, key = normalize_url(body.url), posting_url_key(body.url)
        except AppError as exc:
            if exc.code in _URL_ERRORS:
                raise _url_error(exc) from None
            raise
        if len(url) > URL_MAX or len(key) > URL_MAX:
            raise AppError("invalid_url", "The posting link is too long.", 422, {"fields": ["url"]})
        if route_fragment(body.url):  # the posting is in the anchor: the site root is not it
            raise posting_unreadable()
        return Source(url, key, None)
    text = (body.text or "").strip()
    if not enough_text(text):
        raise posting_too_short()
    return Source(None, None, text)


async def _existing(rt: PostingsRuntime, user_id: str, source: Source) -> str | None:
    async with rt.session_factory() as db:
        repo = PostingRepository(db, user_id)
        if source.url_norm is not None:
            found = await repo.by_url_norm(source.url_norm)
        else:
            found = await repo.by_text_hash(text_digest(source.text or ""))
        return None if found is None else found.id


async def _read_page(rt: PostingsRuntime, user_id: str, url: str) -> str:
    """The page text, read outside a transaction; unreadable or too short: 422."""
    try:
        outcome = await read(rt.research, user_id, None, url)
    except AppError as exc:
        if exc.code in _URL_ERRORS:
            raise _url_error(exc) from None
        if exc.status_code == 429:  # noqa: PLR2004  # web search cap: as is
            raise
        logger.info("Unreadable posting: user %s (%s)", user_id, exc.code)
        raise posting_unreadable() from None
    text = outcome.text.strip()
    if outcome.status != "ok" or not enough_text(text):
        logger.info("Posting unreadable or too short: user %s", user_id)
        raise posting_unreadable()
    return text[:TEXT_MAX]


async def _insert(rt: PostingsRuntime, user_id: str, source: Source, text: str) -> tuple[str, bool]:
    """`(id, created)`; the unique index settles a race: the loser re-reads the winner."""
    async with rt.session_factory() as db:
        row = JobPosting(
            user_id=user_id,
            url=source.url,
            url_norm=source.url_norm,
            source="url" if source.url_norm else "text",
            text=text,
            text_hash=text_digest(text),
            status="analyzing",
        )
        db.add(row)
        try:
            await db.commit()
            return row.id, True
        except IntegrityError:
            await db.rollback()
    winner = await _existing(rt, user_id, source)
    if winner is None:
        raise RuntimeError("winning posting not found after a uniqueness conflict")
    logger.info("Duplicate posting add caught up: user %s, posting %s", user_id, winner)
    return winner, False


async def _answer(
    rt: PostingsRuntime, user_id: str, posting_id: str, created: bool, sid: str | None
) -> PostingCreatedOut:
    async with rt.session_factory() as db:
        posting = await read_posting(db, user_id, posting_id)
    return PostingCreatedOut(posting=posting, created=created, session_id=sid)


async def create_posting(rt: PostingsRuntime, user_id: str, body: PostingIn) -> PostingCreatedOut:
    """See the module. Returns the posting, `created` and the session launched (or `None`)."""
    source = source_of(body)
    async with rt.source_locks.get(user_id, source.key):
        posting_id = await _existing(rt, user_id, source)
        if posting_id is None:
            text = source.text if source.url is None else await _read_page(rt, user_id, source.url)
            posting_id, created = await _insert(rt, user_id, source, text or "")
            if created:
                logger.info("Posting added: user %s, posting %s", user_id, posting_id)
                sid = await launch_new(rt, user_id, posting_id)
                return await _answer(rt, user_id, posting_id, True, sid)
        again = await relaunch(rt, user_id, posting_id, if_needed=True)
        logger.info(
            "Posting already added: user %s, posting %s, relaunched %s",
            user_id,
            posting_id,
            again is not None,
        )
        return await _answer(rt, user_id, posting_id, False, again)
