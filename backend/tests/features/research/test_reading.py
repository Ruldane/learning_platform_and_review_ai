import logging

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models.research import Source
from app.features.research.repository import SourceRepository
from app.features.research.service.errors import QUOTA_CODE, WebQuotaReached
from app.features.research.service.reading import EXCLUDED_REASON, read, record_verdict
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.searching import search
from app.providers.search.fake import FakeSearch
from app.providers.web.base import NO_TEXT_MESSAGE, UrlForbidden, UrlUnreadable, WebDocument
from tests.features.research.conftest import UID, Clock, hit, set_settings
from tests.support.memory import FakeWebReader

Factory = async_sessionmaker[AsyncSession]


def _doc(url: str, title: str = "Attention") -> WebDocument:
    return WebDocument(
        url=url,
        title=title,
        text="Texte principal de la page.",
        author="A. Auteur",
        date="2024-03-04",
        lang="fr",
        description=None,
    )


async def _sources(factory: Factory, session_id: str) -> list[Source]:
    async with factory() as session:
        return await SourceRepository(session, UID).list_for_session(session_id)


async def test_read_ok_creates_pending_source(
    runtime: ResearchRuntime, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    out = await read(runtime, UID, "s1", "HTTPS://Ex.org/a#section")
    assert out.status == "ok" and out.url == "https://ex.org/a" and out.title == "Attention"
    assert out.text and out.reason is None and not out.cached and not out.replayed
    [row] = await _sources(db_session_factory, "s1")
    assert row.id == out.source_id and row.verdict == "pending" and row.kind == "page"
    assert (row.status, row.title, row.author, row.lang, row.published) == (
        "ok",
        "Attention",
        "A. Auteur",
        "fr",
        "2024-03-04",
    )


async def test_unreadable_page_is_reported_with_reason(
    runtime: ResearchRuntime, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/vide"] = UrlUnreadable(NO_TEXT_MESSAGE)
    out = await read(runtime, UID, "s1", "https://ex.org/vide")
    assert out.status == "unreadable" and out.reason == NO_TEXT_MESSAGE and out.source_id
    [row] = await _sources(db_session_factory, "s1")
    assert (row.status, row.reason, row.verdict) == ("unreadable", NO_TEXT_MESSAGE, "pending")


async def test_forbidden_url_is_unreadable_not_500(
    runtime: ResearchRuntime, fake_web: FakeWebReader
) -> None:
    fake_web.pages["http://intranet.example/x"] = UrlForbidden()
    out = await read(runtime, UID, "s1", "http://intranet.example/x")
    assert out.status == "unreadable" and out.reason == UrlForbidden().message


async def test_invalid_url_is_refused_without_reading(
    runtime: ResearchRuntime, fake_web: FakeWebReader
) -> None:
    with pytest.raises(AppError) as error:
        await read(runtime, UID, "s1", "javascript:alert(1)")
    assert error.value.code == "invalid_url" and fake_web.calls == []


async def test_excluded_domain_is_not_read(
    runtime: ResearchRuntime, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    out = await read(runtime, UID, "s1", "https://fr.pinterest.com/pin/1")
    assert fake_web.calls == []
    assert out.status == "unreadable" and out.reason == EXCLUDED_REASON
    assert out.source_id is None and await _sources(db_session_factory, "s1") == []


async def test_page_quota_stops_at_setting(
    runtime: ResearchRuntime, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    await set_settings(db_session_factory, UID, search_max_pages=2)
    await read(runtime, UID, "s1", "https://ex.org/1")  # illisible : compte aussi
    await read(runtime, UID, "s1", "https://ex.org/2")
    with pytest.raises(WebQuotaReached) as error:
        await read(runtime, UID, "s1", "https://ex.org/3")
    assert (error.value.code, error.value.status_code) == (QUOTA_CODE, 429)
    assert error.value.message == "Plafond de 2 pages lues atteint pour cette session."
    assert len(fake_web.calls) == 2
    await read(runtime, UID, "s1", "https://ex.org/1")  # déjà lue : rendue, pas refusée


async def test_same_url_twice_in_session_counts_once(
    runtime: ResearchRuntime, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    a = await read(runtime, UID, "s1", "https://ex.org/a")
    b = await read(runtime, UID, "s1", "https://EX.org/a#autre")
    assert b.replayed and b.source_id == a.source_id and b.text == a.text
    assert len(fake_web.calls) == 1 and len(await _sources(db_session_factory, "s1")) == 1


async def test_cached_page_not_read_again_within_7_days(
    runtime: ResearchRuntime, fake_web: FakeWebReader, clock: Clock, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    await read(runtime, UID, "s1", "https://ex.org/a")
    clock.advance(days=6)
    second = await read(runtime, UID, "s2", "https://ex.org/a")
    assert second.cached and not second.replayed and second.title == "Attention"
    assert len(fake_web.calls) == 1 and len(await _sources(db_session_factory, "s2")) == 1
    clock.advance(days=2)
    assert not (await read(runtime, UID, None, "https://ex.org/a")).cached
    assert len(fake_web.calls) == 2


async def test_unreadable_source_is_never_kept(
    runtime: ResearchRuntime, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/ok"] = _doc("https://ex.org/ok")
    bad = await read(runtime, UID, "s1", "https://ex.org/vide")
    good = await read(runtime, UID, "s1", "https://ex.org/ok")
    assert bad.source_id and good.source_id
    detail = {"authority": 30, "freshness": 20, "depth": 20, "author": 10, "pedagogy": 10}
    async with db_session_factory() as db:
        rejected = await record_verdict(
            db, UID, bad.source_id, score=90, detail=detail, reason="Très bien", summary="…"
        )
        assert rejected.verdict == "rejected" and rejected.reason == bad.reason
        kept = await record_verdict(
            db, UID, good.source_id, score=60, detail=detail, reason="Solide", summary="Résumé"
        )
        assert (kept.verdict, kept.score, kept.reason) == ("kept", 60, "Solide")
        again = await record_verdict(
            db, UID, good.source_id, score=60, detail=detail, reason="Solide", summary="Résumé"
        )
        assert again.id == kept.id and again.verdict == "kept"
        low = await record_verdict(
            db, UID, good.source_id, score=59, detail=detail, reason="Faible", summary="Résumé"
        )
        assert low.verdict == "rejected"
        with pytest.raises(AppError) as error:
            await record_verdict(
                db, "u2", good.source_id, score=90, detail=detail, reason="x", summary="x"
            )
        assert error.value.code == "source_not_found"


async def test_logs_never_contain_query_or_url(
    runtime: ResearchRuntime,
    searxng_fake: FakeSearch,
    fake_web: FakeWebReader,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")  # nos journaux, à tous les niveaux
    searxng_fake.results = {"requete-secrete": [hit("https://secret.example/p", "titre-secret")]}
    fake_web.pages["https://secret.example/p"] = _doc("https://secret.example/p", "titre-secret")
    await search(runtime, UID, "s1", "requete-secrete")
    await read(runtime, UID, "s1", "https://secret.example/p")
    await read(runtime, UID, "s1", "https://secret.example/illisible")
    await read(runtime, UID, "s1", "https://www.pinterest.com/secret")
    assert caplog.records  # les journaux existent bien (identifiants)
    for secret in ("requete-secrete", "secret.example", "titre-secret", "pinterest"):
        assert secret not in caplog.text
