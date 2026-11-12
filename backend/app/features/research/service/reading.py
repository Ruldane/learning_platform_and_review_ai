"""Lecture d'une page pour la recherche web (SPEC 10.2, 10.4) : statut `ok` ou `unreadable` avec
la raison, cache de 7 jours, plafond de pages de la session, ligne `sources` en attente de note.

Aucune transaction pendant la lecture (D66). Journaux : identifiants seulement, jamais l'URL ni
le titre (SPEC 17.2)."""

import logging
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.research import SOURCE_THRESHOLD, PageStatus, Source
from app.features.memory.service.upload import normalize_url
from app.features.research.repository import SourceRepository
from app.features.research.service.cache import CachedPage, WebCache, url_key
from app.features.research.service.domains import host_matches
from app.features.research.service.errors import WebQuotaReached, source_not_found
from app.features.research.service.prefs import ResearchPrefs, load_prefs
from app.features.research.service.runtime import ResearchRuntime
from app.providers.pdf.base import PdfUnreadable
from app.providers.web.base import UrlForbidden, UrlTooLarge, UrlUnreadable, UrlUnsupported

logger = logging.getLogger(__name__)

EXCLUDED_REASON = "Domaine exclu dans les réglages."
# Erreurs de lecture rendues comme une page illisible (leur message, fixe, devient la raison).
_READ_ERRORS = (UrlForbidden, UrlTooLarge, UrlUnsupported, UrlUnreadable, PdfUnreadable)
_MAX_REASON = 300
_MAX_LANG = 8
_MAX_DATE = 32


@dataclass(frozen=True)
class Judged:
    """Verdict déjà posé sur une source de la session (nœud rejoué, seconde lecture)."""

    score: int | None
    verdict: Literal["kept", "rejected"]
    reason: str
    summary: str


@dataclass(frozen=True)
class PageOutcome:
    source_id: str | None
    url: str  # l'URL normalisée
    status: PageStatus
    title: str | None
    text: str
    author: str | None
    date: str | None
    lang: str | None
    reason: str | None
    cached: bool
    replayed: bool
    judged: Judged | None = None


def _judged(source: Source) -> Judged | None:
    if source.verdict == "pending":
        return None
    verdict: Literal["kept", "rejected"] = "kept" if source.verdict == "kept" else "rejected"
    return Judged(source.score, verdict, source.reason or "", source.summary or "")


def _outcome(
    source_id: str | None,
    url: str,
    page: CachedPage,
    *,
    cached: bool,
    replayed: bool,
    judged: Judged | None = None,
) -> PageOutcome:
    return PageOutcome(
        source_id=source_id,
        url=url,
        status=page.status,
        title=page.title,
        text=page.text,
        author=page.author,
        date=page.date,
        lang=page.lang,
        reason=page.reason,
        cached=cached,
        replayed=replayed,
        judged=judged,
    )


def _is_excluded(url: str, settings: ResearchPrefs) -> bool:
    host = urlsplit(url).hostname or ""
    return any(host_matches(host, domain) for domain in settings.excluded)


async def _settings(runtime: ResearchRuntime, user_id: str) -> ResearchPrefs:
    async with runtime.session_factory() as db:
        return await load_prefs(db, user_id)


async def _fetch(runtime: ResearchRuntime, user_id: str, url: str) -> tuple[CachedPage, bool]:
    """Page du cache (rien n'est relu), sinon lue par le lecteur web ; une erreur de lecture
    devient une page illisible avec sa raison. Rend aussi « venait du cache »."""
    async with runtime.session_factory() as db:
        page = await WebCache(db, user_id, now=runtime.now).get_page(url)
    if page is not None:
        return page, True
    try:
        doc = await runtime.providers.web.read(url)
    except _READ_ERRORS as exc:
        logger.info("Page illisible (utilisateur %s) : %s", user_id, exc.code)
        return CachedPage("unreadable", None, "", None, None, None, exc.message), False
    return CachedPage("ok", doc.title, doc.text, doc.author, doc.date, doc.lang, None), False


def _source(session_id: str, url: str, page: CachedPage) -> Source:
    return Source(
        session_id=session_id,
        kind="page",
        url=url,
        url_hash=url_key(url),
        title=page.title,
        author=page.author,
        lang=page.lang[:_MAX_LANG] if page.lang else None,
        published=page.date[:_MAX_DATE] if page.date else None,
        status=page.status,
        verdict="pending",
        reason=page.reason[:_MAX_REASON] if page.reason else None,
    )


async def _save(
    runtime: ResearchRuntime,
    user_id: str,
    url: str,
    found: tuple[CachedPage, bool],
    session_id: str | None,
) -> str | None:
    """Une transaction courte : page mise en cache (si elle vient d'être lue), ligne `sources`
    de la session, purge du cache si due. Rend l'id de la source créée."""
    page, cached = found
    source_id: str | None = None
    async with runtime.session_factory() as db:
        if not cached:
            await WebCache(db, user_id, now=runtime.now).put_page(url, page)
        if session_id is not None:
            source_id = (await SourceRepository(db, user_id).add(_source(session_id, url, page))).id
        await runtime.purge_if_due(db, user_id)
        await db.commit()
    return source_id


async def _in_session(
    runtime: ResearchRuntime, user_id: str, session_id: str, settings: ResearchPrefs, url: str
) -> PageOutcome:
    """À appeler sous `session_lock`. Une URL déjà lue par la session (nœud rejoué) rend sa
    source, et son verdict si elle est déjà notée, sans compter une page de plus ni créer de
    seconde ligne."""
    async with runtime.session_factory() as db:
        repo = SourceRepository(db, user_id)
        known = await repo.get_by_url(session_id, url_key(url))
        count = await repo.count_pages(session_id) if known is None else 0
    if known is not None:
        found = await _fetch(runtime, user_id, url)
        await _save(runtime, user_id, url, found, None)
        return _outcome(
            known.id, url, found[0], cached=found[1], replayed=True, judged=_judged(known)
        )
    if count >= settings.max_pages:
        raise WebQuotaReached(settings.max_pages, "pages")
    found = await _fetch(runtime, user_id, url)
    source_id = await _save(runtime, user_id, url, found, session_id)
    return _outcome(source_id, url, found[0], cached=found[1], replayed=False)


async def read(
    runtime: ResearchRuntime, user_id: str, session_id: str | None, url: str
) -> PageOutcome:
    """Lit `url` (http(s), normalisée ; sinon 422 `invalid_url` ou `url_forbidden`). Un domaine
    exclu n'est jamais lu. Lève `WebQuotaReached` (429) au-delà du plafond de pages."""
    target = normalize_url(url)
    settings = await _settings(runtime, user_id)
    if _is_excluded(target, settings):
        logger.info("Page non lue, domaine exclu (utilisateur %s, session %s)", user_id, session_id)
        page = CachedPage("unreadable", None, "", None, None, None, EXCLUDED_REASON)
        return _outcome(None, target, page, cached=False, replayed=False)
    try:
        if session_id is None:
            found = await _fetch(runtime, user_id, target)
            await _save(runtime, user_id, target, found, None)
            outcome = _outcome(None, target, found[0], cached=found[1], replayed=False)
        else:
            async with runtime.session_lock(user_id, session_id):
                outcome = await _in_session(runtime, user_id, session_id, settings, target)
    except WebQuotaReached as exc:
        logger.warning(
            "Lecture web : utilisateur %s, session %s, %s", user_id, session_id, exc.code
        )
        raise
    logger.info(
        "Lecture web : utilisateur %s, session %s, source %s, statut %s, cache %s, rejouée %s",
        user_id,
        session_id,
        outcome.source_id,
        outcome.status,
        outcome.cached,
        outcome.replayed,
    )
    return outcome


async def record_verdict(
    db: AsyncSession,
    user_id: str,
    source_id: str,
    *,
    score: int | None,
    detail: dict[str, int] | None,
    reason: str,
    summary: str,
) -> Source:
    """Note (bornée à 0..100) et verdict d'une source : `kept` si la note atteint
    `SOURCE_THRESHOLD` et que la page est lisible, sinon `rejected` (une page illisible n'est
    jamais retenue ni citée, SPEC 10.2). `score=None` : note impossible à établir, écartée sans
    note ni détail. Idempotent. La raison d'une page illisible reste celle de la lecture. Le
    commit appartient à l'appelant."""
    source = await SourceRepository(db, user_id).get(source_id)
    if source is None:
        raise source_not_found()
    if score is not None:
        score = max(0, min(100, score))
    readable = source.status == "ok"
    keep = readable and score is not None and score >= SOURCE_THRESHOLD
    source.verdict = "kept" if keep else "rejected"
    source.score = score
    source.score_detail = None if detail is None else dict(detail)
    source.summary = summary
    if readable:
        source.reason = reason[:_MAX_REASON]
    await db.flush()
    return source


async def session_verdicts(db: AsyncSession, user_id: str, session_id: str) -> dict[str, Judged]:
    """Verdicts déjà posés sur les sources de la session de l'utilisateur, par `source_id`."""
    sources = await SourceRepository(db, user_id).list_for_session(session_id)
    return {source.id: judged for source in sources if (judged := _judged(source)) is not None}


async def list_sources(db: AsyncSession, user_id: str, session_id: str) -> list[Source]:
    """Sources d'une session de l'utilisateur, dans l'ordre où elles ont été repérées."""
    return await SourceRepository(db, user_id).list_for_session(session_id)
