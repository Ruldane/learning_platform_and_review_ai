"""`AgentProgramStore` (port `ProgramStore` sur la feature `program`, D88) : contexte du Stratège,
règles de 4.2, versions idempotentes par `(session, revision)`, filtre utilisateur partout."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.agents.tools.plan_schema import PlanDraft
from app.core.errors import AppError
from app.db.models.memory import MemoryItem
from app.db.models.program import PlanVersion, Program, Task
from app.db.models.skills import Skill, UserSkill
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, Factory, add_goal, sample_plan
from tests.support.program import full_week, plan

ME, OTHER = "moi", "autre"


async def _count(factory: Factory, model: type) -> int:
    async with factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def _save(
    store: AgentProgramStore, goal_id: str, draft: PlanDraft, revision: int = 0
) -> tuple[str, int]:
    saved = await store.save_draft(
        ME, "s1", goal_id, draft, revision=revision, start_date=MONDAY, reason=f"r{revision}"
    )
    return saved.program_id, saved.version


async def test_store_save_draft_idempotent_per_revision(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    first = await store.save_draft(
        ME, "s1", rows.goal_id, sample_plan(), revision=0, start_date=MONDAY, reason="v1"
    )
    again = await store.save_draft(
        ME, "s1", rows.goal_id, sample_plan(), revision=0, start_date=MONDAY, reason="v1"
    )
    assert first == again
    assert (first.version, first.weeks, first.total_minutes) == (1, 2, 870)
    assert await _count(db_session_factory, Program) == 1
    assert await _count(db_session_factory, PlanVersion) == 1
    assert await _count(db_session_factory, Task) == 12


async def test_revision_writes_a_new_version_with_its_diff(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    program_id, _ = await _save(store, rows.goal_id, sample_plan())
    shorter = plan([full_week("Bases", [60])], title="Parcours court")
    second_id, version = await _save(store, rows.goal_id, shorter, revision=1)
    assert (second_id, version) == (program_id, 2)
    assert await _count(db_session_factory, Program) == 1
    assert await _count(db_session_factory, Task) == 3
    async with db_session_factory() as db:
        latest = (
            await db.execute(select(PlanVersion).where(PlanVersion.version == 2))
        ).scalar_one()
        program = await db.get(Program, program_id)
    assert latest.diff is not None and latest.diff["weeks_before"] == 2
    assert latest.diff["weeks_after"] == 1 and latest.diff["removed"]
    assert program is not None and program.title == "Parcours court" and program.version == 2


async def test_new_version_is_pending_and_supersedes_the_previous_pending(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    await _save(store, rows.goal_id, sample_plan())
    async with db_session_factory() as db:
        first = (await db.execute(select(PlanVersion))).scalar_one()
        assert (first.status, first.kind) == ("pending", "build")
        first.status, first.accepted_at = "accepted", datetime(2026, 11, 12, tzinfo=UTC)
        await db.commit()
    await _save(store, rows.goal_id, plan([full_week("Bases", [60])]), revision=1)
    await _save(store, rows.goal_id, plan([full_week("Bases", [30])]), revision=2)
    async with db_session_factory() as db:
        rows_ = (
            (await db.execute(select(PlanVersion).order_by(PlanVersion.version))).scalars().all()
        )
    # une version acceptée reste acceptée ; seule une proposition en attente est remplacée
    assert [v.status for v in rows_] == ["accepted", "superseded", "pending"]


async def test_known_skills_merge_user_skills_and_memory(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    async with db_session_factory() as db:
        skill = Skill(user_id=ME, name="Pandas", norm_name="pandas", synonyms=[])
        db.add(skill)
        await db.flush()
        db.add(UserSkill(user_id=ME, skill_id=skill.id, level="declare", evidence=[]))
        for title, level in (("pandas", "valide"), ("SQL avancé", "en_cours")):
            db.add(
                MemoryItem(
                    user_id=ME,
                    kind="acquis",
                    title=title,
                    text=f"Acquis {title}",
                    created_by="archivist",
                    content_hash=f"h-{title}",
                    meta={"level": level},
                )
            )
        db.add(
            MemoryItem(
                user_id=OTHER,
                kind="acquis",
                title="Rust",
                text="Acquis Rust",
                created_by="user",
                content_hash="h-rust",
                meta={"level": "prouve"},
            )
        )
        await db.commit()
    ctx = await store.context(ME, rows.goal_id, [rows.proposal_id], None)
    assert dict(ctx.known_skills) == {"pandas": "valide", "sql avance": "en_cours"}
    assert ctx.budget.cap_minutes == 714 and ctx.language == "fr"
    assert [p.name for p in ctx.proposals] == ["Parcours données"]
    assert ctx.current_plan is None


async def test_context_with_program_reads_current_plan(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    program_id, _ = await _save(store, rows.goal_id, sample_plan())
    ctx = await store.context(ME, rows.goal_id, [rows.proposal_id], program_id)
    assert ctx.current_plan is not None
    assert "Semaine 1 (du 16/11) : Bases" in ctx.current_plan
    assert "17/11 : Lire le chapitre 1 (lire, 120 min)" in ctx.current_plan


async def test_goal_weekly_minutes_scale_the_budget(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME, weekly_minutes=420)
    ctx = await store.context(ME, rows.goal_id, [rows.proposal_id], None)
    assert (ctx.budget.weekday_minutes, ctx.budget.weekend_minutes) == (60, 120)
    problems = await store.check_draft(ME, rows.goal_id, sample_plan())
    assert any("au plus" in problem for problem in problems)


async def test_everything_known_is_nothing_to_plan(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    async with db_session_factory() as db:
        for name in ("pandas", "numpy"):
            skill = Skill(user_id=ME, name=name, norm_name=name, synonyms=[])
            db.add(skill)
            await db.flush()
            db.add(UserSkill(user_id=ME, skill_id=skill.id, level="prouve", evidence=[]))
        await db.commit()
    with pytest.raises(AppError) as caught:
        await _save(store, rows.goal_id, sample_plan())
    assert (caught.value.code, caught.value.status_code) == ("nothing_to_plan", 422)
    assert await _count(db_session_factory, Program) == 0


async def test_budget_too_small_fails_before_the_model(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME, weekly_minutes=60)
    with pytest.raises(AppError) as caught:
        await store.context(ME, rows.goal_id, [rows.proposal_id], None)
    assert caught.value.code == "planning_impossible"


async def test_every_call_checks_the_owner(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    program_id, _ = await _save(store, rows.goal_id, sample_plan())
    other = await add_goal(db_session_factory, OTHER)
    calls = [
        store.context(OTHER, rows.goal_id, [rows.proposal_id], None),
        store.context(ME, rows.goal_id, [other.proposal_id], None),
        store.context(ME, other.goal_id, [rows.proposal_id], None),
        store.check_draft(OTHER, rows.goal_id, sample_plan()),
        store.save_draft(
            OTHER, "s2", rows.goal_id, sample_plan(), revision=0, start_date=None, reason="x"
        ),
        store.save_draft(
            ME, "s1", other.goal_id, sample_plan(), revision=1, start_date=None, reason="x"
        ),
        store.validate(OTHER, "s1", program_id),
    ]
    codes = []
    for call in calls:
        with pytest.raises(AppError) as caught:
            await call
        codes.append(caught.value.code)
    assert codes == [
        "goal_not_found",
        "proposal_not_found",
        "goal_not_found",
        "goal_not_found",
        "goal_not_found",
        "goal_not_found",
        "program_not_found",
    ]
    other_goal_program = await store.context(ME, rows.goal_id, [rows.proposal_id], program_id)
    assert other_goal_program.current_plan is not None


async def test_revision_keeps_the_program_start_date(
    store: AgentProgramStore, db_session_factory: Factory
) -> None:
    rows = await add_goal(db_session_factory, ME)
    program_id, _ = await _save(store, rows.goal_id, sample_plan())
    async with db_session_factory() as db:
        program = await db.get(Program, program_id)
        assert program is not None
        program.start_date = date(2026, 11, 23)
        await db.commit()
    await store.save_draft(
        ME, "s1", rows.goal_id, sample_plan(), revision=1, start_date=MONDAY, reason="r1"
    )
    async with db_session_factory() as db:
        program = await db.get(Program, program_id)
        first = (await db.execute(select(func.min(Task.planned_date)))).scalar_one()
    assert program is not None and program.start_date == date(2026, 11, 23)
    assert first == date(2026, 11, 23)
