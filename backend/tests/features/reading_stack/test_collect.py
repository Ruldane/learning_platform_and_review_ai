from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.reading_stack import ReadingSource
from app.features.reading_stack.service import collect
from app.features.research.service.runtime import ResearchRuntime
from app.providers.search.base import SearchResult
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from tests.features.radar.support import add_users
from tests.support.memory import FakeWebReader
from tests.support.research import FakeFetcher, fake_research_providers

FEED = "https://example.org/feed.xml"
ARTICLE = "https://example.org/guides/python"
PAPER = "https://arxiv.org/abs/1234"
RELEASE = "https://example.org/project/releases/v1"
OWNER = "moi"


async def test_collects_configured_sources_and_reads_each_url_once(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await add_users(db_session_factory, OWNER)
    sources = [
        ReadingSource(user_id=OWNER, label="My Python", kind="topic", value="Python"),
        ReadingSource(user_id=OWNER, label="Guide", kind="site", value="example.org"),
        ReadingSource(user_id=OWNER, label="Versions", kind="rss", value=FEED),
    ]
    web = FakeWebReader(
        pages={
            url: WebDocument(url, "Document fictif", "Le texte principal.", None, None, "fr", None)
            for url in (ARTICLE, PAPER, RELEASE)
        }
    )
    hits = {
        "Python": [SearchResult("Article", ARTICLE, "Un guide.", "test", None)],
        "site:example.org": [
            SearchResult("Même article", ARTICLE + "#titre", "", "test", None),
            SearchResult("Version", RELEASE, "Une version.", "test", None),
        ],
    }
    feed = f"<rss><channel><item><title>Article</title><link>{PAPER}</link></item></channel></rss>"
    fetcher = FakeFetcher({FEED: ("application/rss+xml", feed.encode())})

    async def no_key(_provider: str) -> str | None:
        return None

    search = FakeSearch("searxng", hits)
    providers = fake_research_providers(web, searxng=search, fetcher=fetcher)
    runtime = ResearchRuntime(db_session_factory, providers, no_key)
    result = await collect.collect_web(runtime, OWNER, sources, existing_urls=set())

    assert {item.url: item.kind for item in result} == {
        ARTICLE: "article",
        RELEASE: "release",
        PAPER: "paper",
    }
    assert sum(url == ARTICLE for url, _ in web.calls) == 1
    assert result[0].reason == "My Python"
    assert all(item.text == "Le texte principal." for item in result)
