"""Replan port (SPEC F13, D105). `app.agents` imports no feature (contract 6): it describes here
what the `replan` graph needs (the review, the plan still to do by references, the storing of a
proposal, its acceptance or refusal); the `replan` feature implements it (task 5.9).

The Strategist does not rewrite the plan: it **removes** tasks and **adds** some by reference
(`t12`, `m3`); the code stores everything else (85%, practice, quiz, overflow into "Continued"
weeks). The real identifiers (`task_id`, `module_id`) are never shown to the model (F7): the
graph keeps the context snapshot in its state and hands the port the "reference -> id" table of
that snapshot (`refs`).

Every write is idempotent: `preview` by `(session, revision)`, `apply` and `refuse` by
version; a node replayed after a stop (SPEC 9.4) reads the same thing back, never one more row.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Protocol, Self

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose
from app.agents.tools.plan_schema import CheckpointTaskType, read_checkpoint_task_type
from app.agents.tools.program_port import BudgetView
from app.agents.tools.study_schema import ReplanOption, ReplanTrigger, ReviewState
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.program import TaskType

WEEK_CAP_PERCENT = 85
TASK_REF = r"^t\d{1,4}$"
MODULE_REF = r"^m\d{1,3}$"
# `gap` trigger ("Add to the schedule", D123): the module that receives the additions, created at
# the end of the program on the 1st use then reused, always shown to the model as `m0`.
GAP_MODULE_REF = "m0"
GAP_MODULE_TITLE = "Skills from job postings"
# "Compétences des offres" is the title written before the switch to English: still recognised.
GAP_MODULE_TITLES = frozenset({GAP_MODULE_TITLE, "Compétences des offres"})


def week_cap(available_minutes: int) -> int:
    """Cap of the current week when January only has `available_minutes`: 85%, rounded
    down, in integers (in floats, `0.85 * 300` is 254.99...; here 255)."""
    return available_minutes * WEEK_CAP_PERCENT // 100


@dataclass(frozen=True)
class ModuleRef:
    ref: str  # "m3": the only reference shown to the model
    title: str
    skills: list[str]
    module_id: str  # never rendered to the model (F7)


@dataclass(frozen=True)
class TaskRef:
    """A task still to do (from the current week and the following ones, late ones included)."""

    ref: str  # "t12"
    title: str
    type: TaskType
    minutes: int
    planned_date: date
    module_ref: str
    late: bool  # dated before today and not done
    task_id: str  # never rendered to the model (F7)

    @classmethod
    def from_checkpoint(cls, data: dict[str, Any]) -> Self:
        return cls(
            **{
                **data,
                "type": read_checkpoint_task_type(data["type"]),
                "planned_date": date.fromisoformat(data["planned_date"]),
            }
        )


@dataclass(frozen=True)
class ReviewView:
    """The weekly review that triggered the replan (text written by the code)."""

    entry_id: str
    week_start: date
    text: str
    state: ReviewState
    late_ratio: float


@dataclass(frozen=True)
class ReplanContext:
    program_id: str
    title: str
    goal: str
    deadline: date | None
    budget: BudgetView
    review: ReviewView | None
    options: tuple[ReplanOption, ...]  # empty: nothing to decide
    modules: list[ModuleRef]
    tasks: list[TaskRef]  # to do, from the current week and the following ones, late included
    week_cap_override: int | None  # `week_cap(minutes available this week)`, if given
    message: str | None  # January's text ("I only have 5 hours..."): a note for the Strategist
    skills: tuple[str, ...] = ()  # posting skills to add (`gap` trigger only)

    def refs(self) -> dict[str, str]:
        """Reference (`t12`, `m3`) -> real id, on this snapshot."""
        found = {m.ref: m.module_id for m in self.modules}
        found.update({t.ref: t.task_id for t in self.tasks})
        return found


# --- Structured output of the Strategist ---------------------------------------------------------
# One class per right (D105 (2)): the model only receives the schema of what it may do.
# Summary and done criterion are read text (`Prose`); references and titles stay refused if
# malformed (asked again by `structured_call`).


class ReplanTaskDraft(BaseModel):
    module: str = Field(pattern=MODULE_REF)
    title: str = Field(min_length=3, max_length=120)
    type: CheckpointTaskType
    minutes: int = Field(ge=15, le=120)
    done_criterion: Prose = Field(min_length=3, max_length=200)


def skills_named(task: ReplanTaskDraft, skills: Sequence[str]) -> list[str]:
    """The skills of `skills` that the task names as whole words, in its title or its done
    criterion (case, accents and spaces ignored): "Practise LangGraph" names
    "LangGraph"; "Read about C" does not name "C++"."""
    text = normalize_skill_name(f"{task.title} {task.done_criterion}")
    found: list[str] = []
    for skill in skills:
        norm = normalize_skill_name(skill)
        if norm and re.search(rf"(?<!\w){re.escape(norm)}(?!\w)", text):
            found.append(skill)
    return found


class ReplanSummary(BaseModel):
    """Without option, with "postpone" or "bring forward": a summary alone, fitting is enough."""

    summary: Prose = Field(min_length=1, max_length=600)


class ReplanDrops(ReplanSummary):
    """ "Reduce the scope": removals only."""

    drop: list[Annotated[str, Field(pattern=TASK_REF)]] = Field(default_factory=list, max_length=50)


class ReplanAdds(ReplanSummary):
    """ "Go deeper": additions only."""

    add: list[ReplanTaskDraft] = Field(default_factory=list, max_length=20)


class ReplanDraft(ReplanDrops, ReplanAdds):
    """What the port receives: summary, removals and additions (empty beyond the option rights)."""


# --- What the port returns ----------------------------------------------------------------------


@dataclass(frozen=True)
class WeekLoad:
    rank: int
    start_date: date
    before: int  # minutes planned before the proposal
    after: int  # minutes planned after
    cap: int  # cap of the week (85%, or `week_cap_override` for the current week)


@dataclass(frozen=True)
class PreviewSaved:
    """The proposal, fitted and saved. `empty`: nothing changes. `kept`: removals ignored (the
    last quiz or the last practice of a week, D105). `impossible`: the cap cannot hold a
    practice and the quiz (F10); with `finished`, because the program is finished (no week left
    to replan).

    Life cycle of the written version (D106): `impossible` -> closed status `impossible`;
    `empty` without option -> closed status `empty`; those two are never `pending` nor
    offered to January. Otherwise `pending` (waits for January's answer in the session), and the
    program's previous `pending` ones become `superseded` (D99)."""

    version: int
    empty: bool
    added: int
    removed: int
    moved: int
    weeks_before: int
    weeks_after: int
    loads: list[WeekLoad]
    kept: int = 0
    impossible: bool = False
    finished: bool = False


@dataclass(frozen=True)
class Applied:
    version: int
    stale: bool  # the rows changed since the proposal: nothing is written


class ReplanStore(Protocol):
    async def context(
        self,
        user_id: str,
        program_id: str,
        *,
        trigger: ReplanTrigger,
        review_entry_id: str | None,
        available_minutes: int | None,
        message: str | None,
        skills: Sequence[str] = (),
    ) -> ReplanContext:
        """Program, review and options, budget, modules and tasks to do by reference.
        `gap` trigger: no option, `skills` rendered, target module as `m0`.
        `program_not_found` (404) if the program does not belong to the user."""
        ...

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
        """Resolves the references through `refs` (unknown ones: ignored), applies the option's
        rights (the session's `gap` trigger: additions only, in `m0`, each naming a skill of the
        session; the rest ignored), fits and saves the version (status: see `PreviewSaved`);
        idempotent by `(session, revision)`. Never `planning_impossible`:
        `PreviewSaved.impossible`."""
        ...

    async def apply(self, user_id: str, session_id: str, program_id: str, version: int) -> Applied:
        """Applies the version (idempotent: already accepted -> `stale=False` without writing).
        Rows changed since the proposal, or a version that no longer waits (`superseded` by
        another session, refused, closed) -> `stale=True`, nothing is written, never an error.
        The port takes the program lock itself, before its transaction (F4)."""
        ...

    async def refuse(self, user_id: str, session_id: str, program_id: str, version: int) -> None:
        """The version is refused, the current plan stays (idempotent)."""
        ...


def replan_unavailable() -> AppError:
    return AppError("replan_unavailable", "Replanning is unavailable in this runtime.", 503)


class _NoReplan:
    """Default value of the engine (existing tests, startups without the `replan` feature)."""

    async def context(
        self,
        user_id: str,
        program_id: str,
        *,
        trigger: ReplanTrigger,
        review_entry_id: str | None,
        available_minutes: int | None,
        message: str | None,
        skills: Sequence[str] = (),
    ) -> ReplanContext:
        raise replan_unavailable()

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
        raise replan_unavailable()

    async def apply(self, user_id: str, session_id: str, program_id: str, version: int) -> Applied:
        raise replan_unavailable()

    async def refuse(self, user_id: str, session_id: str, program_id: str, version: int) -> None:
        raise replan_unavailable()


NO_REPLAN: ReplanStore = _NoReplan()
