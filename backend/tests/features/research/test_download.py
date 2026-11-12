"""Copie locale d'un PDF de ressource (D91) : garde SSRF, type PDF seulement, 20 Mo, domaine
exclu jamais contacté ; toute erreur rend `None` sans citer l'adresse dans un journal."""

import logging
from dataclasses import replace

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.research.service.download import download_pdf
from app.features.research.service.runtime import ResearchRuntime
from app.providers.web.base import UrlUnreadable
from tests.features.research.conftest import UID, set_settings
from tests.providers.web.fetch_support import FakeResolver, fetcher_for, never, ok
from tests.support.research import FakeFetcher

PDF = b"%PDF-1.7 contenu %%EOF"
URL = "https://papers.exemple.org/article.pdf"


def _with(runtime: ResearchRuntime, fetcher: object) -> ResearchRuntime:
    runtime.providers = replace(runtime.providers, fetcher=fetcher)  # type: ignore[arg-type]
    return runtime


async def test_free_pdf_is_downloaded(runtime: ResearchRuntime) -> None:
    fake = FakeFetcher({URL: ("application/pdf", PDF)})
    assert await download_pdf(_with(runtime, fake), UID, URL) == PDF
    assert fake.calls == [URL]


async def test_download_refuses_private_address_and_non_pdf(
    runtime: ResearchRuntime, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    # Adresse privée : la vraie garde SSRF refuse avant toute requête.
    resolver = FakeResolver({"intranet.exemple.org": ["10.0.0.7"]})
    fetcher, client = fetcher_for(never, resolver)
    async with client:
        got = await download_pdf(_with(runtime, fetcher), UID, "https://intranet.exemple.org/a.pdf")
    assert got is None
    # Une page HTML n'est pas un PDF : refusée par le type demandé.
    page_fetcher, page_client = fetcher_for(
        lambda request: ok(b"<html></html>", **{"content-type": "text/html"})
    )
    async with page_client:
        assert await download_pdf(_with(runtime, page_fetcher), UID, URL) is None
    # Un « PDF » sans signature est refusé aussi.
    fake = FakeFetcher({URL: ("application/pdf", b"<html>pas un pdf</html>")})
    assert await download_pdf(_with(runtime, fake), UID, URL) is None
    # Nos journaux (httpx est rendu muet par `core.logging`) : jamais l'adresse.
    ours = [r.getMessage() for r in caplog.records if r.name.startswith("app.")]
    assert not any("intranet" in m or "papers" in m for m in ours)
    assert any("url_forbidden" in m for m in ours)


async def test_real_fetcher_returns_a_public_pdf(runtime: ResearchRuntime) -> None:
    fetcher, client = fetcher_for(lambda request: ok(PDF, **{"content-type": "application/pdf"}))
    async with client:
        assert await download_pdf(_with(runtime, fetcher), UID, URL) == PDF


async def test_excluded_domain_is_never_contacted(
    runtime: ResearchRuntime, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await set_settings(db_session_factory, UID, excluded_domains=["exemple.org"])
    fake = FakeFetcher({URL: ("application/pdf", PDF)})
    assert await download_pdf(_with(runtime, fake), UID, URL) is None
    assert fake.calls == []


async def test_any_error_gives_none(runtime: ResearchRuntime) -> None:
    fake = FakeFetcher({URL: UrlUnreadable()})
    assert await download_pdf(_with(runtime, fake), UID, URL) is None

    class Broken:
        async def fetch(self, url: str, **kwargs: object) -> object:
            raise httpx.ConnectError("adresse https://papers.exemple.org dans le message")

    assert await download_pdf(_with(runtime, Broken()), UID, URL) is None
