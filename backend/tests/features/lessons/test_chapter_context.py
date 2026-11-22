from app.agents.tools.plan_schema import NotionDraft
from app.db.models.program import Module
from app.features.lessons.service.store import AgentLessonStore
from app.features.program.service.runtime import ProgramRuntime
from tests.features.lessons.conftest import ME, draft_program
from tests.features.lessons.test_store import publish
from tests.features.program.support import Factory, sample_plan


async def test_brief_follows_chapter_order(
    program_rt: ProgramRuntime, store: AgentLessonStore, db_session_factory: Factory
) -> None:
    draft = sample_plan()
    draft.weeks[0].modules[0].introduces = [
        NotionDraft(name="Attention", definition="Pondérer les informations pertinentes.")
    ]
    draft.weeks[1].modules[0].requires = ["attention"]
    program = await draft_program(program_rt, draft=draft)
    first_id, second_id = program.modules

    first = await store.brief(ME, first_id)
    assert "Chapitre suivant : Module Projet" in first.chapter_context

    await publish(store, program, [])
    async with db_session_factory() as db:
        for module_id in (first_id, second_id):
            row = await db.get(Module, module_id)
            assert row is not None
            row.title = "Nouveau titre choisi"
        await db.commit()
    second = await store.brief(ME, second_id)
    assert "Attention : Pondérer les informations pertinentes." in second.chapter_context
    assert "Chapitre précédent : Module Bases" in second.chapter_context
    assert "L'attention pondère les positions" in second.chapter_context
