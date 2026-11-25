"""Port of the program (D86). `app.agents` imports no feature (contract 6): it describes here what
the `program_builder` graph needs (the Strategist's context, the planning rules, the
draft record, the validation); the `program` feature implements it (task 4.7).

The rules of SPEC 3.4 (85% of the budget, acquired skills, practice and quiz each week) live in the
feature (`check_draft`, `schedule`) and are called by the port: one set of rules for the
Strategist and for January's changes. The plan is in the database, not in the graph state:
a revision rereads the current plan, January's changes included (`current_plan`).

Each write is idempotent: a node replayed after a stop (SPEC 9.4) rewrites the same thing,
never one more row.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.agents.tools.council_port import GoalBrief, ProposalDraft
from app.agents.tools.plan_schema import KnownSkills, PlanDraft
from app.core.errors import AppError


@dataclass(frozen=True)
class BudgetView:
    """A week's budget as the Strategist must respect it (minutes)."""

    weekly_minutes: int
    cap_minutes: int  # 85% of the weekly budget
    weekday_minutes: int  # Monday to Friday, each
    weekend_minutes: int  # the Saturday block; Sunday free
    floor_minutes: int  # 60% of the cap: target load at least, except the last week (D98)


@dataclass(frozen=True)
class ProgramContext:
    goal: GoalBrief
    proposals: list[ProposalDraft]  # one (path chosen) or two (mix)
    budget: BudgetView
    known_skills: KnownSkills
    language: str  # lesson language
    council_minutes: str | None  # Scribe's minutes
    # Current plan as text (January's changes included), for a revision.
    current_plan: str | None


@dataclass(frozen=True)
class DraftSaved:
    program_id: str
    version: int
    weeks: int
    total_minutes: int
    skipped_modules: list[str]  # modules skipped because already acquired
    moved_tasks: int  # tasks postponed to a following week by the scheduling


class ProgramStore(Protocol):
    async def context(
        self, user_id: str, goal_id: str, proposal_ids: Sequence[str], program_id: str | None
    ) -> ProgramContext:
        """Goal, chosen proposals, budget, acquired skills, language, minutes; with
        `program_id`, the current plan as text. `goal_not_found` / `proposal_not_found` (404)."""
        ...

    async def check_draft(self, user_id: str, goal_id: str, draft: PlanDraft) -> list[str]:
        """Problems of the draft (French sentences), per the user's budget."""
        ...

    async def save_draft(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        draft: PlanDraft,
        *,
        revision: int,
        start_date: date | None,
        reason: str,
    ) -> DraftSaved:
        """Stores the draft (acquired skills, 85%, practice and quiz) and records it; idempotent per
        `(session, revision)`: revision 0 creates the program, the next ones a version.
        `planning_impossible` (422) if the budget allows no week."""
        ...

    async def validate(self, user_id: str, session_id: str, program_id: str) -> None:
        """Validates the program (idempotent)."""
        ...


def program_unavailable() -> AppError:
    return AppError("program_unavailable", "The program is unavailable in this runtime.", 503)


class _NoProgram:
    """Engine default value (existing tests, starts without the `program` feature)."""

    async def context(
        self, user_id: str, goal_id: str, proposal_ids: Sequence[str], program_id: str | None
    ) -> ProgramContext:
        raise program_unavailable()

    async def check_draft(self, user_id: str, goal_id: str, draft: PlanDraft) -> list[str]:
        raise program_unavailable()

    async def save_draft(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        draft: PlanDraft,
        *,
        revision: int,
        start_date: date | None,
        reason: str,
    ) -> DraftSaved:
        raise program_unavailable()

    async def validate(self, user_id: str, session_id: str, program_id: str) -> None:
        raise program_unavailable()


NO_PROGRAM: ProgramStore = _NoProgram()
