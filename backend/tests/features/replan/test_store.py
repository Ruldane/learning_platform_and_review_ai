"""Port réel de la replanification (D106) : proposition idempotente et rangée dans le budget,
droits de l'option, versions closes, acceptation périmée ou rejouée, concurrence avec une
modification de January (Review Focus n° 3)."""

import asyncio
import logging
from datetime import date, timedelta

import pytest

from app.agents.tools.replan_port import (
    PreviewSaved,
    ReplanContext,
    ReplanDraft,
    ReplanTaskDraft,
)
from app.agents.tools.study_schema import ReplanOption
from app.core.errors import AppError
from app.features.program.schemas import TaskPatch
from app.features.program.service.editing import move_or_edit_task
from app.features.program.service.programs import get_program
from app.features.program.service.replan_versions import version_history
from app.features.program.service.runtime import ProgramRuntime
from app.features.replan.service.runtime import ReplanRuntime
from app.features.replan.service.store import AgentReplanStore
from tests.features.replan.conftest import (
    CAP,
    ME,
    OTHER,
    TODAY,
    drafted,
    tasks_of,
    validated,
    versions,
    week_loads,
)

DRAFT = ReplanDraft(summary="Je range les retards dans le budget.")


async def _context(store: AgentReplanStore, program_id: str, **over: object) -> ReplanContext:
    args: dict[str, object] = {"review_entry_id": None, "available_minutes": None, "message": None}
    args.update(over)
    return await store.context(ME, program_id, trigger="message", **args)  # type: ignore[arg-type]


async def _preview(
    store: AgentReplanStore,
    program_id: str,
    draft: ReplanDraft = DRAFT,
    *,
    session: str = "s-replan",
    revision: int = 0,
    option: ReplanOption | None = None,
    available: int | None = None,
) -> PreviewSaved:
    ctx = await _context(store, program_id, available_minutes=available)
    return await store.preview(
        ME, session, program_id, draft, refs=ctx.refs(), option=option, revision=revision,
        reason="Message de January", week_cap_override=ctx.week_cap_override,
    )  # fmt: skip


async def test_context_refs_late_tasks_and_ownership(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    ctx = await _context(store, program_id, available_minutes=300)
    assert [t.ref for t in ctx.tasks] == [f"t{n}" for n in range(1, len(ctx.tasks) + 1)]
    assert all(t.late == (t.planned_date < TODAY) for t in ctx.tasks) and ctx.tasks[0].late
    assert ctx.week_cap_override == 255 and ctx.budget.cap_minutes == CAP
    assert [m.ref for m in ctx.modules] == ["m1", "m2"] and ctx.review is None
    other = await validated(program_rt, OTHER)
    with pytest.raises(AppError) as exc:
        await _context(store, other)
    assert exc.value.code == "program_not_found"
    draft = await drafted(program_rt, "tiers")  # brouillon : 409 `program_not_validated`
    with pytest.raises(AppError) as exc:
        await store.context(
            "tiers", draft, trigger="message", review_entry_id=None, available_minutes=None,
            message=None,
        )  # fmt: skip
    assert exc.value.code == "program_not_validated"


async def test_preview_is_idempotent_by_session_and_revision(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    ctx = await _context(store, program_id)
    first = await store.preview(
        ME, "s-replan", program_id, DRAFT, refs=ctx.refs(), option=None, revision=0,
        reason="Message de January", week_cap_override=None,
    )  # fmt: skip
    again = await store.preview(
        ME, "s-replan", program_id, DRAFT, refs=ctx.refs(), option=None, revision=0,
        reason="Message de January", week_cap_override=None,
    )  # fmt: skip
    assert again == first and first.version == 2 and not first.empty and first.moved > 0
    assert await versions(program_rt.session_factory, program_id) == [
        {"version": 1, "kind": "build", "status": "accepted"},
        {"version": 2, "kind": "replan", "status": "pending"},
    ]
    async with program_rt.session_factory() as db:
        view = await get_program(db, ME, program_id)
    assert view.version == 1 and view.diff is None  # une proposition ne paraît jamais appliquée


async def test_preview_ignores_unknown_refs_and_option_rights(
    store: AgentReplanStore, program_rt: ProgramRuntime, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    program_id = await validated(program_rt)
    ctx = await _context(store, program_id)
    added = ReplanTaskDraft(
        module="m1", title="Lire un article secret", type="lire", minutes=30,
        done_criterion="Notes prises",
    )  # fmt: skip
    ghost = added.model_copy(update={"module": "m9"})
    deepen = ReplanDraft(summary="Approfondir", drop=["t1"], add=[added, ghost])
    saved = await _preview(store, program_id, deepen, option="deepen")
    assert saved.removed == 0 and saved.added == 1  # retrait hors droits ignoré, m9 inconnu
    quiz = next(t.ref for t in ctx.tasks if t.type == "quiz")
    reduce = ReplanDraft(summary="Réduire", drop=[quiz, "t99"])
    last = await _preview(store, program_id, reduce, option="reduce_scope", revision=1)
    assert (last.removed, last.kept) == (0, 1)  # le dernier quiz d'une semaine reste
    assert "1 référence(s) inconnue(s)" in caplog.text and "secret" not in caplog.text


async def test_apply_on_changed_rows_is_stale(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    version = (await _preview(store, program_id)).version
    week2 = [t for t in await tasks_of(program_rt.session_factory, program_id)
             if t.planned_date >= date(2026, 11, 23)]  # fmt: skip
    moved = week2[0]
    target = moved.planned_date + timedelta(days=1)
    await move_or_edit_task(program_rt, ME, moved.id, TaskPatch(planned_date=target))
    applied = await store.apply(ME, "s-replan", program_id, version)
    assert applied.stale and applied.version == version
    after = {t.id: t.planned_date for t in await tasks_of(program_rt.session_factory, program_id)}
    assert after[moved.id] == target  # rien n'est écrit : le déplacement de January reste
    assert (await versions(program_rt.session_factory, program_id))[-1]["status"] == "pending"


async def test_apply_twice_is_idempotent(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    version = (await _preview(store, program_id)).version
    first = await store.apply(ME, "s-replan", program_id, version)
    rows = {t.id: t.planned_date for t in await tasks_of(program_rt.session_factory, program_id)}
    again = await store.apply(ME, "s-replan", program_id, version)
    assert not first.stale and not again.stale
    assert {t.id: t.planned_date
            for t in await tasks_of(program_rt.session_factory, program_id)} == rows  # fmt: skip
    todo = [t for t in await tasks_of(program_rt.session_factory, program_id) if t.status == "todo"]
    assert all(t.planned_date >= TODAY for t in todo)  # plus aucun retard
    assert all(load <= CAP for load in await week_loads(program_rt.session_factory, program_id))
    async with program_rt.session_factory() as db:
        view = await get_program(db, ME, program_id)
    assert view.version == version and view.diff is not None and view.diff.moved
    assert view.weekday_minutes == 120  # l'instantané d'une replanification garde le budget
    await store.refuse(ME, "s-replan", program_id, version)  # déjà acceptée : rien
    assert (await versions(program_rt.session_factory, program_id))[-1]["status"] == "accepted"


async def test_concurrent_apply_and_task_move_never_exceed_cap(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    version = (await _preview(store, program_id)).version
    tasks = await tasks_of(program_rt.session_factory, program_id)
    # January avance une lecture de la semaine 2 au samedi de la semaine 1, déjà chargée.
    late = next(t for t in tasks if t.planned_date >= date(2026, 11, 23) and t.type == "lire")
    patch = TaskPatch(planned_date=date(2026, 11, 21))
    results = await asyncio.gather(
        store.apply(ME, "s-replan", program_id, version),
        move_or_edit_task(program_rt, ME, late.id, patch),
        return_exceptions=True,
    )
    assert not isinstance(results[0], BaseException)
    assert all(load <= CAP for load in await week_loads(program_rt.session_factory, program_id))


async def test_half_done_week_proposal_respects_budget(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    tasks = await tasks_of(program_rt.session_factory, program_id)
    for task in [t for t in tasks if t.planned_date < TODAY][:1]:
        await move_or_edit_task(program_rt, ME, task.id, TaskPatch(status="done"))
    version = (await _preview(store, program_id)).version
    async with program_rt.session_factory() as db:
        row = (await version_history(db, ME, program_id))[0]
    loads = row.week_loads["loads"] if row.week_loads else []
    assert loads and all(w["after"] <= w["cap"] <= CAP for w in loads)
    assert loads[0]["before"] == 665
    assert not (await store.apply(ME, "s-replan", program_id, version)).stale
    assert all(load <= CAP for load in await week_loads(program_rt.session_factory, program_id))
    done = [t for t in await tasks_of(program_rt.session_factory, program_id) if t.status == "done"]
    assert [t.planned_date for t in done] == [tasks[0].planned_date]  # faite : jamais déplacée


async def test_closed_versions_never_pending(
    store: AgentReplanStore, program_rt: ProgramRuntime, replan_rt: ReplanRuntime
) -> None:
    program_id = await validated(program_rt, start=date(2026, 11, 23))  # rien en retard
    empty = (await _preview(store, program_id)).version
    impossible = (await _preview(store, program_id, revision=1, available=60)).version
    statuses = [v["status"] for v in await versions(program_rt.session_factory, program_id)]
    assert statuses == ["accepted", "empty", "impossible"]
    assert (await store.apply(ME, "s-replan", program_id, impossible)).stale  # jamais d'erreur
    assert empty == 2


async def test_second_session_supersedes_and_first_accept_is_stale(
    store: AgentReplanStore, program_rt: ProgramRuntime
) -> None:
    program_id = await validated(program_rt)
    first = (await _preview(store, program_id, session="s-a")).version
    second = (await _preview(store, program_id, session="s-b")).version
    assert (await store.apply(ME, "s-a", program_id, first)).stale  # remplacée : périmée
    assert not (await store.apply(ME, "s-b", program_id, second)).stale
    assert [v["status"] for v in await versions(program_rt.session_factory, program_id)] == [
        "accepted",
        "superseded",
        "accepted",
    ]
