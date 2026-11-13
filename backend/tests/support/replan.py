"""Faux port de la replanification (`FakeReplanStore`) en mémoire, idempotent comme le contrat, et
le plan de test (`replan_context`) : deux semaines de deux modules, référencés `t1…t7` et `m1…m2`.
Le rangement est grossier (pas celui de 5.9) mais suit ses règles visibles : retrait du dernier
quiz ou de la dernière pratique d'une semaine ignoré et compté, plafond de la semaine en cours,
version vide `impossible` si ce plafond ne tient pas une pratique et le quiz (F10). Aucun réseau
ni LLM."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any

from app.agents.tools.program_port import BudgetView
from app.agents.tools.replan_port import (
    Applied,
    ModuleRef,
    PreviewSaved,
    ReplanContext,
    ReplanDraft,
    ReviewView,
    TaskRef,
    WeekLoad,
    week_cap,
)
from app.agents.tools.study_schema import ReplanOption, ReplanTrigger, ReviewState
from app.core.errors import AppError
from app.db.models.program import TaskType
from app.features.replan.service.review import options_for

PROGRAM_ID = "eeeeeeee-bbbb-cccc-dddd-000000000001"
REVIEW_ID = "eeeeeeee-bbbb-cccc-dddd-000000000002"
MONDAY = date(2026, 11, 16)
REVIEW_TEXT = "Semaine du 09/11 : 6 h prévues, 2 h faites, 2 tâches sur 7, aucun quiz."
GOAL = "Devenir AI product engineer"
MIN_WEEK = 65  # une pratique (45 min) et le quiz (20 min)
_TASKS: list[tuple[str, TaskType, int, int, str]] = [  # titre, type, minutes, jour, module
    ("Lire le tutoriel Python", "lire", 120, 0, "m1"),
    ("Lire le guide des tests", "lire", 90, 1, "m1"),
    ("Pratiquer les fonctions", "pratiquer", 45, 2, "m1"),
    ("Faire le quiz Python", "quiz", 20, 5, "m1"),
    ("Lire la doc de l'API", "lire", 60, 7, "m2"),
    ("Pratiquer un appel d'API", "pratiquer", 45, 9, "m2"),
    ("Faire le quiz API", "quiz", 20, 12, "m2"),
]


def task_id(ref: str) -> str:
    return f"task-id-{ref}"


def replan_context(state: ReviewState = "on_track", *, late: int = 0) -> ReplanContext:
    """Le plan de test ; `late` : les premières tâches en retard ; `state` : le bilan."""
    modules = [
        ModuleRef("m1", "Bases de Python", ["Python"], "module-id-m1"),
        ModuleRef("m2", "API de LLM", ["API de LLM"], "module-id-m2"),
    ]
    tasks = [
        TaskRef(
            f"t{n}",
            title,
            kind,
            minutes,
            MONDAY + timedelta(days=day),
            module,
            n <= late,
            task_id(f"t{n}"),
        )
        for n, (title, kind, minutes, day, module) in enumerate(_TASKS, start=1)
    ]
    ratio = 0.5 if state in ("late", "late_twice") else 0.0
    review = ReviewView(REVIEW_ID, MONDAY - timedelta(days=7), REVIEW_TEXT, state, ratio)
    budget = BudgetView(840, 714, 120, 240, 428)
    return ReplanContext(
        PROGRAM_ID,
        "Parcours IA",
        GOAL,
        date(2027, 3, 1),
        budget,
        review,
        options_for(state),
        modules,
        tasks,
        None,
        None,
    )


@dataclass(frozen=True)
class PreviewCall:
    session_id: str
    revision: int
    option: ReplanOption | None
    draft: ReplanDraft
    reason: str
    week_cap_override: int | None
    refs: dict[str, str]


def _week(day: date) -> date:
    return day - timedelta(days=day.weekday())


@dataclass
class FakeReplanStore:
    """`plans` : le contexte par (utilisateur, programme) ; `context_calls` : les arguments de
    chaque lecture ; `previews` : les versions écrites (une par `(session, revision)`) ;
    `applied` / `refused` : les versions effectives, `apply_calls` / `refuse_calls` tous les
    appels. `stale_applies` : nombre d'acceptations à rendre périmées ; `after_stale` : le plan
    que January laisse avant une acceptation périmée (relu ensuite) ; `block_after_apply` fige
    l'appel après l'écriture (arrêt du back en plein nœud)."""

    plans: dict[tuple[str, str], ReplanContext] = field(default_factory=dict)
    context_calls: list[dict[str, Any]] = field(default_factory=list)
    previews: list[PreviewCall] = field(default_factory=list)
    saved: dict[tuple[str, int], PreviewSaved] = field(default_factory=dict)
    preview_calls: int = 0
    applied: list[int] = field(default_factory=list)
    apply_calls: int = 0
    stale_applies: int = 0
    after_stale: ReplanContext | None = None
    block_after_apply: bool = False
    refused: list[int] = field(default_factory=list)
    refuse_calls: int = 0

    def add(self, user_id: str, ctx: ReplanContext) -> None:
        self.plans[(user_id, ctx.program_id)] = ctx

    def _plan(self, user_id: str, program_id: str) -> ReplanContext:
        found = self.plans.get((user_id, program_id))
        if found is None:
            raise AppError("program_not_found", "Programme introuvable.", 404)
        return found

    async def context(
        self,
        user_id: str,
        program_id: str,
        *,
        trigger: ReplanTrigger,
        review_entry_id: str | None,
        available_minutes: int | None,
        message: str | None,
    ) -> ReplanContext:
        ctx = self._plan(user_id, program_id)
        self.context_calls.append(
            {"trigger": trigger, "available_minutes": available_minutes, "message": message}
        )
        if trigger == "message":
            ctx = replace(ctx, review=None, options=())
        elif ctx.review is None or ctx.review.entry_id != review_entry_id:
            raise AppError("review_not_found", "Bilan introuvable.", 404)
        cap = week_cap(available_minutes) if available_minutes else None
        return replace(ctx, week_cap_override=cap, message=message)

    async def preview(
        self,
        user_id: str,
        session_id: str,
        program_id: str,
        draft: ReplanDraft,
        *,
        refs: Mapping[str, str],
        option: ReplanOption | None,
        revision: int,
        reason: str,
        week_cap_override: int | None,
    ) -> PreviewSaved:
        ctx = self._plan(user_id, program_id)
        self.preview_calls += 1
        key = (session_id, revision)
        if key not in self.saved:
            call = PreviewCall(
                session_id, revision, option, draft, reason, week_cap_override, dict(refs)
            )
            self.previews.append(call)
            version = 1 + len(self.saved) + 1
            self.saved[key] = _range(ctx, call, version)
        return self.saved[key]

    async def apply(self, user_id: str, session_id: str, program_id: str, version: int) -> Applied:
        self._plan(user_id, program_id)
        self.apply_calls += 1
        if version in self.applied:
            return Applied(version, stale=False)
        if self.stale_applies:
            self.stale_applies -= 1
            if self.after_stale is not None:
                self.plans[(user_id, program_id)] = self.after_stale
            return Applied(version, stale=True)
        self.applied.append(version)
        if self.block_after_apply:
            await asyncio.Event().wait()
        return Applied(version, stale=False)

    async def refuse(self, user_id: str, session_id: str, program_id: str, version: int) -> None:
        self._plan(user_id, program_id)
        self.refuse_calls += 1
        if version not in self.refused:
            self.refused.append(version)


def _dropped(ctx: ReplanContext, call: PreviewCall) -> tuple[list[TaskRef], int]:
    """Les tâches retirées, et les retraits ignorés (dernier quiz ou dernière pratique)."""
    ids = set(call.refs.get(ref) for ref in call.draft.drop)
    left = list(ctx.tasks)
    removed: list[TaskRef] = []
    kept = 0
    for task in [t for t in ctx.tasks if t.task_id in ids]:
        same = [
            t
            for t in left
            if t.type == task.type and _week(t.planned_date) == _week(task.planned_date)
        ]
        if task.type in ("pratiquer", "quiz") and len(same) == 1:
            kept += 1
            continue
        left.remove(task)
        removed.append(task)
    return removed, kept


def _range(ctx: ReplanContext, call: PreviewCall, version: int) -> PreviewSaved:
    weeks = sorted({_week(t.planned_date) for t in ctx.tasks})
    override = call.week_cap_override
    if override is not None and override < MIN_WEEK:
        return PreviewSaved(version, True, 0, 0, 0, len(weeks), len(weeks), [], impossible=True)
    removed, kept = _dropped(ctx, call)
    added = [t for t in call.draft.add if t.module in call.refs]
    loads: list[WeekLoad] = []
    moved = sum(1 for t in ctx.tasks if t.late) + (1 if call.option == "advance" else 0)
    for rank, start in enumerate(weeks, start=1):
        before = sum(t.minutes for t in ctx.tasks if _week(t.planned_date) == start)
        after = before - sum(t.minutes for t in removed if _week(t.planned_date) == start)
        after += sum(t.minutes for t in added) if rank == 1 else 0
        cap = override if rank == 1 and override is not None else ctx.budget.cap_minutes
        if after > cap:  # la lecture la plus longue part à la semaine suivante
            moved += 1
            after -= max(t.minutes for t in ctx.tasks if _week(t.planned_date) == start)
        loads.append(WeekLoad(rank, start, before, after, cap))
    weeks_after = len(weeks) + (1 if call.option == "push_deadline" else 0)
    empty = not (removed or added or moved) and weeks_after == len(weeks)
    return PreviewSaved(
        version, empty, len(added), len(removed), moved, len(weeks), weeks_after, loads, kept
    )
