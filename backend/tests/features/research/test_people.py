"""Praticiens repérés par l'Éclaireur (SPEC 10.3, D84) : une ligne `sources` de `kind` `person`,
unique par session, isolée par utilisateur, sans autre donnée que le nom, le rôle et où il
publie."""

import logging

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.web_port import PersonFound
from app.db.models.research import Source
from app.features.research.repository import SourceRepository
from app.features.research.service.cache import url_key
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.people import record_person
from app.features.research.service.reading import session_verdicts
from app.features.research.service.runtime import ResearchRuntime

ADA = PersonFound(
    name="Ada Lovelace",
    role="Ingénieure, autrice de la doc",
    url="https://docs.exemple.org/attention",
    where=("docs.exemple.org", "blog.exemple.fr"),
)


async def test_record_person_is_idempotent_and_isolated(db: AsyncSession) -> None:
    first = await record_person(db, "u1", "s1", ADA)
    again = await record_person(db, "u1", "s1", ADA)
    await db.commit()
    assert again.id == first.id
    assert (first.kind, first.title, first.author, first.summary) == (
        "person",
        "Ada Lovelace",
        "Ingénieure, autrice de la doc",
        "docs.exemple.org ; blog.exemple.fr",
    )
    assert (first.status, first.verdict, first.score, first.score_detail) == (
        "ok",
        "kept",
        None,
        None,
    )
    assert (first.lang, first.published, first.reason) == (None, None, None)
    other_session = await record_person(db, "u1", "s2", ADA)
    other_user = await record_person(db, "u2", "s1", ADA)
    await db.commit()
    assert len({first.id, other_session.id, other_user.id}) == 3
    assert [s.id for s in await SourceRepository(db, "u1").list_for_session("s1")] == [first.id]
    assert len(await SourceRepository(db, "u2").list_for_session("s1")) == 1


async def test_person_does_not_collide_with_the_page_of_the_same_address(
    db: AsyncSession,
) -> None:
    """La page lue de la même adresse garde sa ligne ; deux praticiens d'une même page aussi
    (équipe), et le décompte des pages ne compte pas les personnes."""
    repo = SourceRepository(db, "u1")
    page = await repo.add(
        Source(session_id="s1", kind="page", url=ADA.url, url_hash=url_key(ADA.url), status="ok")
    )
    ada = await record_person(db, "u1", "s1", ADA)
    grace = await record_person(
        db, "u1", "s1", PersonFound("Grace Hopper", "Amirale", ADA.url, ("docs.exemple.org",))
    )
    await db.commit()
    assert len({page.id, ada.id, grace.id}) == 3
    assert await repo.count_pages("s1") == 1
    verdicts = await session_verdicts(db, "u1", "s1")
    assert verdicts[ada.id].verdict == "kept"


async def test_record_person_logs_ids_only(
    db: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await record_person(db, "u1", "s1", ADA)
    text = caplog.text
    assert "Ada" not in text and "exemple" not in text and "Ingénieure" not in text


async def test_gateway_add_person_returns_the_same_id_when_replayed(
    runtime: ResearchRuntime, db: AsyncSession
) -> None:
    gateway = AgentWebGateway(runtime)
    first = await gateway.add_person("u1", "s1", ADA)
    assert await gateway.add_person("u1", "s1", ADA) == first
    rows = await SourceRepository(db, "u1").list_for_session("s1")
    assert [(r.id, r.kind) for r in rows] == [(first, "person")]
