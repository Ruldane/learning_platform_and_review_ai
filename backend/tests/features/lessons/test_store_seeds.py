"""Fiche du module (`AgentLessonStore.brief`) : les pages officielles du module en tête des
adresses de départ, sans doublon, et les API anciennes à ne montrer qu'en encadré."""

from app.db.models.learning import Goal
from app.db.models.program import Module
from app.features.lessons.service.store import AgentLessonStore
from app.features.program.service.runtime import ProgramRuntime
from tests.features.lessons.conftest import ME, draft_program
from tests.features.lessons.test_store import add_sources
from tests.features.program.support import Factory


async def test_official_pages_come_first_in_the_seeds(
    program_rt: ProgramRuntime, store: AgentLessonStore, db_session_factory: Factory
) -> None:
    program = await draft_program(program_rt)
    council = "c" * 36
    sources = await add_sources(db_session_factory, council, 7)
    official = ["https://docs.exemple.org/guide", sources[3].url, "https://docs.exemple.org/api"]
    async with db_session_factory() as db:
        goal = await db.get(Goal, program.goal_id)
        module = await db.get(Module, program.modules[0])
        assert goal is not None and module is not None
        goal.council_session_id = council
        module.official_urls = official
        module.legacy = ["LLMChain", "LCEL"]
        await db.commit()
    brief = await store.brief(ME, program.modules[0])
    assert brief.seed_urls[:3] == tuple(official)  # en tête, sans doublon avec le Conseil
    assert len(brief.seed_urls) == 5 and len(set(brief.seed_urls)) == 5
    assert brief.legacy == ("LLMChain", "LCEL")


async def test_seeds_without_official_pages_are_unchanged(
    program_rt: ProgramRuntime, store: AgentLessonStore
) -> None:
    program = await draft_program(program_rt)
    brief = await store.brief(ME, program.modules[0])
    assert brief.seed_urls == () and brief.legacy == ()
