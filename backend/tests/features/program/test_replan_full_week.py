from datetime import datetime, timedelta

from app.features.program.repository import TaskRepository
from app.features.program.service.programs import load
from app.features.program.service.replan_versions import Proposal, apply_version, save_proposal
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, WEEK1_LOAD, add_goal, sample_plan

USER = "full-week-owner"


async def _full_week(rt: ProgramRuntime) -> tuple[str, str]:
    goal = await add_goal(rt.session_factory, USER)
    original = sample_plan()
    draft = original.model_copy(update={"weeks": [original.weeks[0]]})
    saved = await AgentProgramStore(rt).save_draft(
        USER,
        "build-full-week",
        goal.goal_id,
        draft,
        revision=0,
        start_date=MONDAY,
        reason="Programme",
    )
    async with rt.session_factory() as db:
        program = await load(db, USER, saved.program_id)
        for task in program.tasks:
            task.status = "done"
        extra = await TaskRepository(db, USER).add(
            module_id=program.modules[0].id,
            program_id=saved.program_id,
            rank=len(program.tasks),
            title="Pratiquer un exercice supplémentaire",
            type="practice",
            minutes=45,
            done_criterion="Écrire la solution",
            planned_date=MONDAY + timedelta(days=5),
        )
        await db.commit()
        return saved.program_id, extra.id


async def test_full_week_appends_week_only_when_proposal_is_accepted(
    program_rt: ProgramRuntime,
) -> None:
    program_id, task_id = await _full_week(program_rt)
    proposal = Proposal(
        session_id="replan-full-week",
        revision=0,
        reason="Semaine pleine",
        drop=set(),
        add=[],
        option=None,
        week_cap_override=WEEK1_LOAD,
        review_entry_id=None,
        today=MONDAY,
    )
    proposed = await save_proposal(program_rt, USER, program_id, proposal)

    assert not proposed.impossible and (proposed.weeks_before, proposed.weeks_after) == (1, 2)
    async with program_rt.session_factory() as db:
        before = await load(db, USER, program_id)
        assert len(before.weeks) == 1
        extra = next(t for t in before.tasks if t.id == task_id)
        assert extra.planned_date == MONDAY + timedelta(days=5)

    now = datetime.fromisoformat("2026-11-16T09:00:00+00:00")
    applied = await apply_version(program_rt, USER, program_id, proposed.version, now, MONDAY)
    assert not applied.stale
    async with program_rt.session_factory() as db:
        after = await load(db, USER, program_id)
        assert len(after.weeks) == 2
        suite = after.weeks[-1].start_date
        assert suite == MONDAY + timedelta(days=7)
        extra = next(t for t in after.tasks if t.id == task_id)
        assert suite <= extra.planned_date < suite + timedelta(days=7)
        assert sum(t.minutes for t in after.tasks if t.status == "done") == WEEK1_LOAD
