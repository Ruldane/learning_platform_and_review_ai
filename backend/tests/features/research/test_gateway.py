"""Passerelle web des agents : conversion des issues du service en types du port, note calculée
par le code, isolation entre utilisateurs, aucun appel réseau (faux fournisseurs)."""

import logging
from dataclasses import replace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.web_port import (
    CRITERIA_MAX,
    QUOTA_CODE,
    SEARCH_UNAVAILABLE_CODE,
    WebGateway,
)
from app.core.errors import AppError
from app.features.research.repository import SourceRepository
from app.features.research.service import errors
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.runtime import ResearchRuntime
from app.providers.search.fake import FakeSearch
from app.providers.web.base import UrlUnreadable, WebDocument
from tests.features.research.conftest import OTHER, UID, hit, set_settings
from tests.support.memory import FakeWebReader

Factory = async_sessionmaker[AsyncSession]
FULL = dict(CRITERIA_MAX)


def _doc(url: str) -> WebDocument:
    return WebDocument(url, "Attention", "Texte de la page.", "Ada", "2025-01-02", "fr", None)


@pytest.fixture
def gateway(runtime: ResearchRuntime) -> WebGateway:
    return AgentWebGateway(runtime)


async def test_error_codes_match_the_engine_port() -> None:
    assert QUOTA_CODE == errors.QUOTA_CODE
    assert errors.NoSearchProvider().code == SEARCH_UNAVAILABLE_CODE


async def test_search_returns_cleaned_query_and_preferred_flag(
    gateway: WebGateway, searxng_fake: FakeSearch, db_session_factory: Factory
) -> None:
    await set_settings(db_session_factory, UID, preferred_domains=["python.org"])
    searxng_fake.results["attention"] = [
        hit("https://blog.fr/a", "Blog"),
        hit("https://docs.python.org/3/", "Doc"),
    ]
    found = await gateway.search(UID, "s1", "attention Jane Doé", lang="fr", time_range="decade")
    assert found.query == "attention" and found.provider == "searxng"
    assert [(h.url, h.preferred) for h in found.hits] == [
        ("https://docs.python.org/3/", True),
        ("https://blog.fr/a", False),
    ]


async def test_search_down_raises_search_unavailable(
    gateway: WebGateway, searxng_fake: FakeSearch
) -> None:
    with pytest.raises(AppError) as exc:
        await gateway.search(UID, "s1", "attention")
    assert exc.value.code == SEARCH_UNAVAILABLE_CODE and "moteur" in exc.value.message


async def test_read_ok_and_replay_give_the_same_source(
    gateway: WebGateway, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    first = await gateway.read(UID, "s1", "https://ex.org/a")
    again = await gateway.read(UID, "s1", "https://ex.org/a")
    assert first.status == "ok" and first.source_id is not None
    assert (first.title, first.author, first.date, first.lang) == (
        "Attention",
        "Ada",
        "2025-01-02",
        "fr",
    )
    assert again.source_id == first.source_id
    async with db_session_factory() as db:
        assert len(await SourceRepository(db, UID).list_for_session("s1")) == 1


async def test_read_excluded_domain_is_unreadable_without_source_id(
    gateway: WebGateway, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    await set_settings(db_session_factory, UID, excluded_domains=["ex.org"])
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    page = await gateway.read(UID, "s1", "https://ex.org/a")
    assert page.source_id is None and page.status == "unreadable"
    assert page.reason and page.text == "" and fake_web.calls == []
    async with db_session_factory() as db:
        assert await SourceRepository(db, UID).list_for_session("s1") == []


async def test_judge_sums_bounded_criteria_and_keeps_from_60(
    gateway: WebGateway, fake_web: FakeWebReader
) -> None:
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    fake_web.pages["https://ex.org/b"] = _doc("https://ex.org/b")
    a = await gateway.read(UID, "s1", "https://ex.org/a")
    b = await gateway.read(UID, "s1", "https://ex.org/b")
    assert a.source_id and b.source_id
    kept = await gateway.judge(
        UID,
        "s1",
        a.source_id,
        criteria={**FULL, "authority": 99, "bonus": 50},
        reason="Solide.",
        summary="R",
    )
    assert (kept.score, kept.verdict, kept.reason) == (
        100,
        "kept",
        "Solide.",
    )  # 99 -> 30, bonus ignoré
    low = {"authority": 20, "freshness": 10, "depth": 10, "author": 10, "pedagogy": 9}
    rejected = await gateway.judge(
        UID, "s1", b.source_id, criteria=low, reason="Maigre.", summary="R"
    )
    assert (rejected.score, rejected.verdict) == (59, "rejected")
    again = await gateway.judge(
        UID, "s1", b.source_id, criteria={**low, "pedagogy": 10}, reason="Ok.", summary="R"
    )
    assert (again.score, again.verdict) == (60, "kept")  # seuil inclus, jugement rejouable


async def test_judge_without_criteria_rejects_without_score(
    gateway: WebGateway, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    """Page dont la note n'a pas pu être établie (sortie du modèle invalide) : écartée, sans
    note ni détail, avec la raison donnée (revue phase 3, I2)."""
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    page = await gateway.read(UID, "s1", "https://ex.org/a")
    assert page.source_id
    verdict = await gateway.judge(
        UID, "s1", page.source_id, criteria=None, reason="Note impossible.", summary=""
    )
    assert (verdict.score, verdict.verdict, verdict.reason) == (
        None,
        "rejected",
        "Note impossible.",
    )
    async with db_session_factory() as db:
        row = await SourceRepository(db, UID).get(page.source_id)
    assert row is not None
    assert (row.verdict, row.score, row.score_detail) == ("rejected", None, None)


async def test_judge_never_keeps_an_unreadable_page(
    gateway: WebGateway, fake_web: FakeWebReader
) -> None:
    fake_web.pages["https://ex.org/x"] = UrlUnreadable()
    page = await gateway.read(UID, "s1", "https://ex.org/x")
    assert page.status == "unreadable" and page.source_id
    verdict = await gateway.judge(
        UID, "s1", page.source_id, criteria=FULL, reason="Top.", summary="R"
    )
    assert verdict.verdict == "rejected" and verdict.reason == page.reason


async def test_gateway_isolated_between_users(
    gateway: WebGateway, fake_web: FakeWebReader, db_session_factory: Factory
) -> None:
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    page = await gateway.read(UID, "s1", "https://ex.org/a")
    assert page.source_id
    with pytest.raises(AppError) as exc:
        await gateway.judge(OTHER, "s1", page.source_id, criteria=FULL, reason="x", summary="x")
    assert exc.value.code == "source_not_found"
    async with db_session_factory() as db:
        assert (await SourceRepository(db, UID).get(page.source_id)).verdict == "pending"  # type: ignore[union-attr]
        assert await SourceRepository(db, OTHER).list_for_session("s1") == []


async def test_limits_come_from_the_user_settings(
    gateway: WebGateway, db_session_factory: Factory
) -> None:
    await set_settings(
        db_session_factory,
        UID,
        search_max_queries=3,
        search_max_pages=7,
        preferred_domains=["a.org"],
    )
    limits = await gateway.limits(UID)
    assert (limits.max_queries, limits.max_pages, limits.preferred) == (3, 7, ("a.org",))
    assert limits.languages == ("fr", "en")


async def test_gateway_logs_carry_no_query_url_or_title(
    gateway: WebGateway,
    searxng_fake: FakeSearch,
    fake_web: FakeWebReader,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    searxng_fake.results["requete secrete"] = [hit("https://ex.org/a", "Titre secret")]
    fake_web.pages["https://ex.org/a"] = _doc("https://ex.org/a")
    await gateway.search(UID, "s1", "requete secrete")
    page = await gateway.read(UID, "s1", "https://ex.org/a")
    assert page.source_id
    await gateway.judge(
        UID, "s1", page.source_id, criteria=FULL, reason="Bien.", summary="Résumé secret"
    )
    logs = " | ".join(r.getMessage() for r in caplog.records if r.name.startswith("app."))
    assert logs  # des journaux ont bien été écrits
    assert "secrete" not in logs and "ex.org" not in logs and "Attention" not in logs


class _OpenSessions:
    """Fabrique de sessions qui compte les sessions ouvertes (une session ouverte = une
    transaction possible, donc un verrou d'écriture SQLite tenu pendant l'appel réseau)."""

    def __init__(self, inner: Factory) -> None:
        self.inner, self.open = inner, 0

    def __call__(self) -> "_Tracked":
        return _Tracked(self)


class _Tracked:
    def __init__(self, owner: _OpenSessions) -> None:
        self.owner = owner
        self.session = owner.inner()

    async def __aenter__(self) -> AsyncSession:
        self.owner.open += 1
        return await self.session.__aenter__()

    async def __aexit__(self, *exc: object) -> None:
        self.owner.open -= 1
        await self.session.__aexit__(*exc)


async def test_no_database_session_is_open_during_network_calls(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, fake_web: FakeWebReader
) -> None:
    tracker = _OpenSessions(runtime.session_factory)
    runtime.session_factory = tracker  # type: ignore[assignment]
    seen: list[int] = []

    class Spy(FakeWebReader):
        async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
            seen.append(tracker.open)
            return _doc(url)

    original = searxng_fake.search

    async def spy_search(*args: object, **kwargs: object) -> list:  # type: ignore[type-arg]
        seen.append(tracker.open)
        return await original(*args, **kwargs)  # type: ignore[arg-type]

    searxng_fake.results["attention"] = [hit("https://ex.org/a")]
    searxng_fake.search = spy_search  # type: ignore[method-assign]
    runtime.providers = replace(runtime.providers, searxng=searxng_fake, web=Spy())
    gateway = AgentWebGateway(runtime)
    await gateway.search(UID, "s1", "attention")
    await gateway.read(UID, "s1", "https://ex.org/a")
    assert seen == [0, 0]
