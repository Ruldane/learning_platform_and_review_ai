"""Collecte de liens publics avec les limites et les fournisseurs de la recherche."""

import logging
from collections.abc import Sequence
from urllib.parse import urlsplit

from app.core.errors import AppError
from app.db.models.reading_stack import ReadingKind, ReadingSource
from app.features.memory.service.upload import normalize_url
from app.features.reading_stack.service.feeds import FeedEntry, parse_feed
from app.features.reading_stack.types import CollectedItem
from app.features.research.service.domains import host_matches
from app.features.research.service.prefs import load_prefs
from app.features.research.service.reading import read
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.searching import search

logger = logging.getLogger(__name__)
MAX_ITEMS = 32
MAX_PER_SOURCE = 6
ARTICLE_TEXT_LIMIT = 16_000
_FEED_TYPES = ("application/rss+xml", "application/atom+xml", "application/xml", "text/xml")


def usable_url(url: str, excluded: Sequence[str] = ()) -> str | None:
    try:
        target = normalize_url(url)
    except AppError:
        return None
    host = urlsplit(target).hostname or ""
    if len(target) > 2000 or any(host_matches(host, domain) for domain in excluded):
        return None
    return target


def _kind(url: str) -> ReadingKind:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if any(host_matches(host, domain) for domain in ("arxiv.org", "doi.org", "biorxiv.org")):
        return "paper"
    if "/releases/" in parts.path or "/changelog/" in parts.path:
        return "release"
    return "article"


async def _candidates(
    rt: ResearchRuntime, user_id: str, source: ReadingSource, excluded: Sequence[str]
) -> list[FeedEntry]:
    if source.kind == "rss":
        url = usable_url(source.value, excluded)
        if url is None:
            return []
        response = await rt.providers.fetcher.fetch(url, content_types=_FEED_TYPES)
        if usable_url(response.final_url, excluded) is None:
            return []
        return parse_feed(response.body, response.final_url)
    query = f"site:{source.value}" if source.kind == "site" else source.value
    result = await search(rt, user_id, None, query, time_range="week")
    return [FeedEntry(hit.result.url, hit.result.title, hit.result.snippet) for hit in result.hits]


async def _read_article(
    rt: ResearchRuntime, user: str, url: str, hit: FeedEntry, label: str
) -> CollectedItem | None:
    page = await read(rt, user, None, url)
    text = page.text.strip() if page.status == "ok" else ""
    title = (page.title or hit.title).strip()
    if not title or not (text or hit.summary.strip()):
        return None
    return CollectedItem(
        _kind(url),
        url,
        title[:240],
        (hit.summary.strip() or text)[:600],
        text[:ARTICLE_TEXT_LIMIT],
        label[:240],
    )


async def _from_source(
    rt: ResearchRuntime,
    user_id: str,
    source: ReadingSource,
    excluded: Sequence[str],
    seen: set[str],
) -> list[CollectedItem]:
    try:
        candidates = await _candidates(rt, user_id, source, excluded)
    except AppError as exc:
        logger.warning(
            "Collecte de lecture : utilisateur %s, source %s, %s", user_id, source.id, exc.code
        )
        return []
    articles: list[CollectedItem] = []
    attempts = 0
    for hit in candidates:
        url = usable_url(hit.url, excluded)
        if url is None or url in seen:
            continue
        if source.kind == "site" and not host_matches(urlsplit(url).hostname or "", source.value):
            continue
        attempts += 1
        seen.add(url)
        article = await _read_article(rt, user_id, url, hit, source.label)
        if article is not None:
            articles.append(article)
        if attempts >= MAX_PER_SOURCE:
            break
    return articles


async def collect_web(
    rt: ResearchRuntime, user_id: str, sources: Sequence[ReadingSource], existing_urls: set[str]
) -> list[CollectedItem]:
    async with rt.session_factory() as db:
        excluded = (await load_prefs(db, user_id)).excluded
    articles: list[CollectedItem] = []
    seen = set(existing_urls)
    for source in sources:
        articles.extend(await _from_source(rt, user_id, source, excluded, seen))
        if len(articles) >= MAX_ITEMS:
            break
    return articles[:MAX_ITEMS]
