"""Suivi d'un quiz dans le programme (D101) : tâches posées au premier jour qui garde la règle de
la semaine (85 %, pratique, quiz), jamais un dimanche ; non placées comptées ; tâches cochées.
Le verrou du programme est tenu par l'appelant (F4)."""

from datetime import date, timedelta

from app.features.program.service.followup import (
    FollowupTask,
    add_followup,
    tick_retry,
    tick_tasks,
)
from app.features.program.service.programs import load
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import CAP, MONDAY, add_goal, sample_plan

ME = "moi"


async def _program(rt: ProgramRuntime) -> tuple[str, list[str]]:
    rows = await add_goal(rt.session_factory, ME)
    saved = await AgentProgramStore(rt).save_draft(
        ME, "s-draft", rows.goal_id, sample_plan(), revision=0, start_date=MONDAY, reason="v1"
    )
    async with rt.session_factory() as db:
        loaded = await load(db, ME, saved.program_id)
    return saved.program_id, [m.id for m in loaded.modules]


def _revision(earliest: date, minutes: int = 20) -> FollowupTask:
    return FollowupTask("Réviser : pandas", "lire", minutes, "Relu.", earliest)


async def test_followup_fills_week_then_spills_within_cap(program_rt: ProgramRuntime) -> None:
    program_id, modules = await _program(program_rt)
    tasks = [_revision(MONDAY + timedelta(days=1)) for _ in range(3)]
    async with program_rt.program_lock(ME, program_id), program_rt.session_factory() as db:
        days, unplaced = await add_followup(db, program_rt, ME, modules[0], tasks)
        await db.commit()
    # Semaine 1 à 665 min pour 714 : deux tâches de 20 tiennent, la troisième va au lundi suivant.
    assert days == [MONDAY + timedelta(days=1)] * 2 + [MONDAY + timedelta(days=7)]
    assert unplaced == 0
    async with program_rt.session_factory() as db:
        loaded = await load(db, ME, program_id)
    assert all(loaded.week_load(week) <= CAP for week in loaded.weeks)
    added = [t for t in loaded.tasks if t.title == "Réviser : pandas"]
    assert {t.module_id for t in added} == {modules[0]} and len(added) == 3


async def test_followup_skips_sunday_and_counts_unplaced(program_rt: ProgramRuntime) -> None:
    program_id, modules = await _program(program_rt)
    sunday_w1 = MONDAY + timedelta(days=6)
    tasks = [
        _revision(sunday_w1, minutes=40),  # dimanche sauté, semaine 1 pleine : lundi 23
        _revision(MONDAY + timedelta(days=13)),  # dimanche de la dernière semaine : aucun jour
        _revision(MONDAY + timedelta(days=1), minutes=600),  # ne tient dans aucune semaine
    ]
    async with program_rt.program_lock(ME, program_id), program_rt.session_factory() as db:
        days, unplaced = await add_followup(db, program_rt, ME, modules[0], tasks)
        await db.commit()
    assert (days, unplaced) == ([MONDAY + timedelta(days=7)], 2)


async def test_tick_tasks_and_retry_are_idempotent(program_rt: ProgramRuntime) -> None:
    program_id, modules = await _program(program_rt)
    retry = FollowupTask("Refaire le quiz : Module Bases", "quiz", 20, "Refait.", MONDAY)
    async with program_rt.program_lock(ME, program_id), program_rt.session_factory() as db:
        await add_followup(db, program_rt, ME, modules[0], [retry])
        loaded = await load(db, ME, program_id)
        first = loaded.tasks_of_module(modules[0])[0]
        assert await tick_tasks(db, program_rt, ME, [first.id, first.id, "inconnue"]) == [
            first.title
        ]
        assert await tick_tasks(db, program_rt, ME, [first.id]) == []
        assert await tick_retry(db, program_rt, ME, modules[0]) == 1
        assert await tick_retry(db, program_rt, ME, modules[0]) == 0
        await db.commit()
    async with program_rt.session_factory() as db:
        assert await tick_tasks(db, program_rt, "autre", [first.id]) == []
