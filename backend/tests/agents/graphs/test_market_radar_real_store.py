"""Le parcours `market_radar` sur le port réel (`AgentRadarStore`, D160) : l'adaptateur et le
graphe s'accordent (repères de page `p10` et plus, extractions rangées sous le repère de la
page, rapport du port), sans doublon à la reprise, sur la vraie base."""

from collections.abc import AsyncIterator

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import Cipher
from app.db.models.daily import RadarRun
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.store import AgentRadarStore
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.keys_service import DbKeyReader
from app.providers.web.base import WebDocument
from tests.agents.graphs.radar_support import MakeRadar, analyst, batch, blocked, postings
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.memory import FakeWebReader
from tests.support.radar import ROLE, RUN_ID, ZONE
from tests.support.research import fake_research_providers


@pytest.fixture
async def real_store(
    db_session_factory: async_sessionmaker[AsyncSession], user_id: str, radar_runner: MakeRadar
) -> AsyncIterator[tuple[AgentRadarStore, FakeWebReader]]:
    """Le port réel sur la base de test, avec le relevé `RUN_ID` déjà créé. `radar_runner` ajoute
    les utilisateurs de la base avant."""
    async with db_session_factory() as db:
        db.add(
            RadarRun(
                id=RUN_ID,
                user_id=user_id,
                role=ROLE,
                zone=ZONE,
                role_norm=ROLE.casefold(),
                zone_norm=ZONE.casefold(),
                trigger="manual",
            )
        )
        await db.commit()
    web = FakeWebReader()
    keys = DbKeyReader(db_session_factory, Cipher(Fernet.generate_key()), {})
    research = ResearchRuntime(db_session_factory, fake_research_providers(web), keys)
    yield (
        AgentRadarStore(
            RadarRuntime(db_session_factory, RecordingLauncher(db_session_factory), research)
        ),
        web,
    )


async def test_graph_runs_on_the_real_store_with_page_refs_past_p5(
    radar_runner: MakeRadar,
    real_store: tuple[AgentRadarStore, FakeWebReader],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store, web = real_store
    pages = postings(12) + blocked(3)
    for page in pages:
        if page.status == "ok":
            web.pages[page.url] = WebDocument(page.url, "T", page.text, None, None, "fr", None)
    models = analyst(batch(5), batch(5), batch(2))
    run = await radar_runner(models, sources=pages, store=store)
    await run.wait_status("completed")
    async with db_session_factory() as db:
        row = (await db.execute(select(RadarRun).where(RadarRun.id == RUN_ID))).scalar_one()
    assert row.status == "done" and row.finished_at is not None
    assert (row.read_count, row.blocked_count, row.not_postings, row.analyzed) == (12, 3, 0, 12)
    assert (row.queries, row.candidates) == (12, 15)
    refs = [entry["ref"] for entry in row.postings]
    assert sorted(refs, key=lambda ref: int(ref[1:])) == [f"p{n}" for n in range(1, 16)]
    analysed = [entry for entry in row.postings if entry.get("skills")]
    assert len(analysed) == 12 and all("text" not in entry for entry in row.postings)
    assert any(int(entry["ref"][1:]) >= 10 for entry in analysed)  # repères à deux chiffres
    assert [t["skill"] for t in row.ranking][:2] == ["Python", "RAG"]
    assert row.blocked_domains == {"bloque.example.org": 3}
    [done] = await run.events("run.completed")
    assert done["summary"].startswith("12 offres lues, 3 bloquées, 12 analysées.")


async def test_failed_extraction_pages_are_counted_not_hidden(
    radar_runner: MakeRadar,
    real_store: tuple[AgentRadarStore, FakeWebReader],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Un lot que l'Analyste ne sait pas rendre valide : ses pages sont lues, pas analysées."""
    store, web = real_store
    pages = postings(10)
    for page in pages:
        web.pages[page.url] = WebDocument(page.url, "T", page.text, None, None, "fr", None)
    models = analyst("pas du JSON", "toujours pas", '{"items": 3}', batch(5), default=0)
    run = await radar_runner(models, sources=pages, store=store)
    await run.wait_status("completed")
    async with db_session_factory() as db:
        row = (await db.execute(select(RadarRun).where(RadarRun.id == RUN_ID))).scalar_one()
    assert (row.read_count, row.analyzed) == (10, 5)
    assert sum(entry["read"] == "extract_failed" for entry in row.postings) == 5
