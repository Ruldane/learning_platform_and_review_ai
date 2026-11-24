"""Étape et justification des semaines, pages officielles et API anciennes des modules : rangées
avec le brouillon du Stratège, rendues par la vue du programme."""

from datetime import date

from sqlalchemy import select

from app.agents.tools.plan_schema import ModuleDraft, PlanDraft, SkillDraft, WeekDraft
from app.db.models.program import Module, Week
from app.features.program.service.programs import get_program
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, Factory, add_goal
from tests.support.program import task

ME = "moi"
URLS = ["https://docs.exemple.org/models", "https://docs.exemple.org/messages"]


def _tasks(minutes: int = 40) -> list:
    return [
        task("Lire la doc", minutes=minutes),
        task("Pratiquer les modèles", "practice", 45),
        task("Faire le quiz", "quiz", 20),
    ]


def staged_plan() -> PlanDraft:
    first = WeekDraft(
        theme="Modèles et messages",
        objective="Appeler un modèle",
        deliverable="Un script",
        stage="foundations",
        rationale="Tout le reste s'appuie sur l'appel d'un modèle.",
        modules=[
            ModuleDraft(
                title="Appeler un modèle",
                skills=["LangChain"],
                tasks=_tasks(),
                official_urls=URLS,
                legacy=["LLMChain"],
            )
        ],
    )
    plain = WeekDraft(
        theme="Les outils",
        objective="Donner des outils",
        deliverable="Un agent",
        modules=[ModuleDraft(title="Outils", skills=["Outils"], tasks=_tasks())],
    )
    return PlanDraft(
        title="LangChain de zéro à expert",
        weeks=[first, plain],
        skills=[SkillDraft(name="LangChain", domain="Agents")],
    )


async def test_save_draft_keeps_the_new_fields(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    saved = await store.save_draft(
        ME, "s1", rows.goal_id, staged_plan(), revision=0, start_date=MONDAY, reason="v1"
    )
    async with db_session_factory() as db:
        weeks = list((await db.execute(select(Week).order_by(Week.rank))).scalars())
        modules = list((await db.execute(select(Module))).scalars())
        view = await get_program(db, ME, saved.program_id)
    assert [(w.stage, w.rationale) for w in weeks] == [
        ("foundations", "Tout le reste s'appuie sur l'appel d'un modèle."),
        (None, None),
    ]
    by_title = {m.title: m for m in modules}
    assert by_title["Appeler un modèle"].official_urls == URLS
    assert by_title["Appeler un modèle"].legacy == ["LLMChain"]
    assert by_title["Outils"].official_urls == [] and by_title["Outils"].legacy == []
    first, second = view.weeks
    assert first.stage == "foundations" and first.rationale is not None
    assert second.stage is None and second.rationale is None
    assert first.modules[0].official_urls == URLS and first.modules[0].legacy == ["LLMChain"]
    assert second.modules[0].official_urls == [] and second.modules[0].legacy == []


async def test_a_revision_keeps_the_fields_too(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    await store.save_draft(
        ME, "s1", rows.goal_id, staged_plan(), revision=0, start_date=date(2026, 11, 16), reason="a"
    )
    checkpoint = staged_plan().model_dump(mode="json")
    checkpoint["weeks"][0]["stage"] = "fondations"
    saved = await store.save_draft(
        ME,
        "s1",
        rows.goal_id,
        PlanDraft.model_validate(checkpoint),
        revision=1,
        start_date=None,
        reason="b",
    )
    async with db_session_factory() as db:
        view = await get_program(db, ME, saved.program_id)
    assert view.weeks[0].stage == "foundations"
    assert view.weeks[0].modules[0].official_urls == URLS
