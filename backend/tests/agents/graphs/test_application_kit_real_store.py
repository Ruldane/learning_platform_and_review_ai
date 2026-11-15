"""Le parcours `application_kit` sur le port réel (`AgentKitStore`, D143) : les sept branches
rangent en parallèle dans la vraie base, sans doublon ; le dossier garde l'ordre de ses pages ;
une pièce modifiée par January n'est jamais refaite à la relance."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.kit_schema import KIT_KINDS
from app.db.models.applications import Application, ApplicationEvent, KitItem
from app.db.models.career import MasterProfile
from app.db.models.postings import Company
from app.features.applications.service.kit import patch_piece
from app.features.applications.service.kit_store import AgentKitStore
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.postings.service.rules import company_key
from scripts.sample_posting import POSTING_TEXT
from tests.agents.graphs.kit_support import MakeKit
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.kit import APPLICATION_ID, COMPANY, TITLE
from tests.support.text_claims import P


@pytest.fixture
async def kit_store(
    db_session_factory: async_sessionmaker[AsyncSession], user_id: str
) -> AsyncIterator[AgentKitStore]:
    """Le port réel sur la base de test, avec la fiche et le profil validé de January."""
    async with db_session_factory() as db:
        db.add(
            Application(
                id=APPLICATION_ID,
                user_id=user_id,
                company=COMPANY,
                company_norm=company_key(COMPANY),
                title=TITLE,
                posting_text=POSTING_TEXT,
            )
        )
        db.add(
            MasterProfile(
                user_id=user_id,
                version=1,
                status="validated",
                data=P.model_dump(mode="json"),
                source="january",
            )
        )
        await db.commit()
    yield AgentKitStore(
        ApplicationsRuntime(db_session_factory, RecordingLauncher(db_session_factory))
    )


async def pieces(factory: async_sessionmaker[AsyncSession]) -> list[KitItem]:
    async with factory() as db:
        return list((await db.execute(select(KitItem))).scalars())


async def end_events(factory: async_sessionmaker[AsyncSession]) -> list[ApplicationEvent]:
    async with factory() as db:
        stmt = select(ApplicationEvent).where(ApplicationEvent.kind == "kit")
        return list((await db.execute(stmt)).scalars())


async def test_graph_writes_seven_pieces_through_the_real_store(
    kit_runner: MakeKit, db_session_factory: async_sessionmaker[AsyncSession], user_id: str
) -> None:
    run = await kit_runner()
    await run.wait_status("completed")
    stored = await pieces(db_session_factory)
    assert sorted(row.kind for row in stored) == sorted(KIT_KINDS)  # sept lignes, jamais dix
    assert {row.session_id for row in stored} == {run.sid}
    announced = {event["artifact_id"] for event in await run.events("artifact.ready")}
    assert announced == {row.id for row in stored}  # chaque pièce est annoncée par son id
    [done] = await end_events(db_session_factory)
    assert done.ref_id == run.sid and done.text.startswith("Kit de candidature terminé : ")


async def test_the_dossier_pages_keep_their_rank_through_the_store(
    kit_runner: MakeKit,
    kit_store: AgentKitStore,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
) -> None:
    run = await kit_runner()
    await run.wait_status("completed")
    async with db_session_factory() as db:
        company = (await db.execute(select(Company))).scalar_one()
    urls = [source["url"] for source in company.dossier_sources]
    assert len(urls) == 4 and company.dossier is not None
    brief = next(row for row in await pieces(db_session_factory) if row.kind == "company_brief")
    positions = [brief.content.index(url) for url in urls]
    assert positions == sorted(positions)  # la liste du dossier suit le rang des citations
    # Relu pour une relance : dossier repris, pages dans le même ordre (`[n]` = rang + 1).
    ctx = await kit_store.context(user_id, APPLICATION_ID)
    assert [source.url for source in ctx.company_dossier_sources] == urls


async def test_relaunch_redoes_only_the_pieces_january_did_not_edit(
    kit_runner: MakeKit,
    kit_store: AgentKitStore,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
) -> None:
    first = await kit_runner()
    await first.wait_status("completed")
    rt = ApplicationsRuntime(db_session_factory, RecordingLauncher(db_session_factory))
    await patch_piece(rt, user_id, APPLICATION_ID, "letter", "Ma lettre à moi, écrite à la main.")
    second = await kit_runner()
    await second.wait_status("completed")
    stored = {row.kind: row for row in await pieces(db_session_factory)}
    assert len(stored) == 7
    assert (stored["letter"].content, stored["letter"].edited) == (
        "Ma lettre à moi, écrite à la main.",
        True,
    )
    assert stored["letter"].session_id == first.sid
    assert {row.session_id for kind, row in stored.items() if kind != "letter"} == {second.sid}
    assert len(await second.events("artifact.ready")) == 6  # la lettre gardée n'est pas annoncée
    events = await end_events(db_session_factory)
    assert [e.ref_id for e in events] == [first.sid, second.sid]
    assert events[1].text.endswith("1 gardée(s) telle(s) quelle(s).")
