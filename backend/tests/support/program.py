"""Fabriques de brouillons de programme pour les tests de planification, et faux port du
programme (`FakeProgramStore`) pour les tests du parcours `program_builder`."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

from app.agents.tools.council_port import GoalBrief, ProposalDraft
from app.agents.tools.plan_schema import (
    ModuleDraft,
    PlanDraft,
    SkillDraft,
    TaskDraft,
    WeekDraft,
)
from app.agents.tools.program_port import BudgetView, DraftSaved, ProgramContext
from app.core.errors import AppError
from app.db.models.program import TaskType
from app.db.models.skills import SkillLevel
from app.features.program.service.budget import Budget
from app.features.program.service.planning import (
    ScheduledPlan,
    check_draft,
    next_monday,
    schedule,
)
from app.features.program.service.rules import floor_minutes
from tests.support.council import GOAL_ID, GOAL_TEXT

MONDAY = date(2026, 11, 16)


def task(title: str, kind: TaskType = "lire", minutes: int = 30) -> TaskDraft:
    return TaskDraft(title=title, type=kind, minutes=minutes, done_criterion="Notes prises")


def module(title: str, tasks: list[TaskDraft], skills: list[str] | None = None) -> ModuleDraft:
    return ModuleDraft(title=title, skills=skills or [title], tasks=tasks)


def week(theme: str, modules: list[ModuleDraft]) -> WeekDraft:
    return WeekDraft(theme=theme, objective="Savoir faire", deliverable="Un dépôt", modules=modules)


def plan(weeks: list[WeekDraft], title: str = "Parcours IA") -> PlanDraft:
    return PlanDraft(title=title, weeks=weeks, skills=[SkillDraft(name="Python", domain="Code")])


def full_week(theme: str, minutes: list[int]) -> WeekDraft:
    """Une semaine d'un module : des lectures, puis la pratique et le quiz de la semaine."""
    tasks = [task(f"Lire le chapitre {i}", minutes=m) for i, m in enumerate(minutes, start=1)]
    tasks += [task(f"Pratiquer {theme}", "pratiquer", 45), task("Faire le quiz", "quiz", 20)]
    return week(theme, [module(f"Module {theme}", tasks)])


# --- Faux port du programme (`ProgramStore`) ------------------------------------------------------


def plan_text(plan: ScheduledPlan) -> str:
    """Le plan rangé en texte, comme le port le rend au Stratège pour une révision."""
    lines: list[str] = []
    for week in plan.weeks:
        lines.append(f"Semaine {week.rank} (du {week.start_date:%d/%m}) : {week.theme}")
        lines += [
            f"- {t.planned_date:%d/%m} : {t.title} ({t.type}, {t.minutes} min)" for t in week.tasks
        ]
    return "\n".join(lines)


@dataclass(frozen=True)
class SavedDraft:
    session_id: str
    revision: int
    draft: PlanDraft
    plan: ScheduledPlan
    reason: str
    start_date: date


@dataclass
class FakeProgramStore:
    """En mémoire, idempotent comme le contrat, sur les VRAIES règles de 4.2 (`check_draft`,
    `schedule`). `drafts` : versions enregistrées (une par `(session, revision)`), `save_calls`
    tous les appels ; `validated` : validations effectives, `validate_calls` tous les appels ;
    `plans` : le plan courant en texte par programme (un test peut le réécrire : modifications de
    January) ; `contexts` : le `program_id` de chaque lecture du contexte. `block_after_save` /
    `block_after_validate` figent l'appel après l'écriture (arrêt du back en plein nœud). Chaque
    appel vérifie que l'objectif (et les propositions) sont à l'utilisateur (404 sinon)."""

    budget: Budget = field(default_factory=lambda: Budget(120, 240))  # 840 min, plafond 714
    known: dict[str, SkillLevel] = field(default_factory=dict)
    minutes: str | None = "Le Conseil s'accorde sur un socle puis un projet."
    goals: dict[tuple[str, str], GoalBrief] = field(default_factory=dict)
    proposals: dict[str, tuple[str, ProposalDraft]] = field(default_factory=dict)
    drafts: list[SavedDraft] = field(default_factory=list)
    saved: dict[tuple[str, int], DraftSaved] = field(default_factory=dict)
    programs: dict[str, str] = field(default_factory=dict)  # session → programme
    plans: dict[str, str] = field(default_factory=dict)
    contexts: list[str | None] = field(default_factory=list)
    save_calls: int = 0
    block_after_save: bool = False
    validated: list[str] = field(default_factory=list)
    validate_calls: int = 0
    block_after_validate: bool = False

    def add_goal(self, user_id: str, proposals: list[ProposalDraft]) -> list[str]:
        """L'objectif `GOAL_ID` de l'utilisateur et ses propositions ; rend leurs ids."""
        self.goals[(user_id, GOAL_ID)] = GoalBrief(
            GOAL_ID, GOAL_TEXT, "AI product engineer", None, None, {"q1": "Le soir surtout"}
        )
        ids = [uuid4().hex for _ in proposals]
        self.proposals.update({pid: (user_id, p) for pid, p in zip(ids, proposals, strict=True)})
        return ids

    def _goal(self, user_id: str, goal_id: str) -> GoalBrief:
        brief = self.goals.get((user_id, goal_id))
        if brief is None:
            raise AppError("goal_not_found", "Objectif introuvable.", 404)
        return brief

    def _view(self) -> BudgetView:
        b = self.budget
        floor = floor_minutes(b.cap_minutes)
        return BudgetView(
            b.weekly_minutes, b.cap_minutes, b.weekday_minutes, b.weekend_minutes, floor
        )

    async def context(
        self, user_id: str, goal_id: str, proposal_ids: Sequence[str], program_id: str | None
    ) -> ProgramContext:
        goal = self._goal(user_id, goal_id)
        chosen = [self.proposals.get(pid) for pid in proposal_ids]
        if any(item is None or item[0] != user_id for item in chosen):
            raise AppError("proposal_not_found", "Proposition introuvable.", 404)
        self.contexts.append(program_id)
        drafts = [item[1] for item in chosen if item is not None]
        current = self.plans.get(program_id) if program_id else None
        return ProgramContext(
            goal, drafts, self._view(), dict(self.known), "fr", self.minutes, current
        )

    async def check_draft(self, user_id: str, goal_id: str, draft: PlanDraft) -> list[str]:
        self._goal(user_id, goal_id)
        return check_draft(draft, self.budget)

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
        self._goal(user_id, goal_id)
        self.save_calls += 1
        if (session_id, revision) not in self.saved:
            start = start_date or next_monday(date.today())
            scheduled = schedule(draft, self.budget, self.known, start)
            if not scheduled.weeks:
                raise AppError("nothing_to_plan", "Tout ce programme est déjà acquis.", 422)
            program_id = self.programs.setdefault(session_id, uuid4().hex)
            self.drafts.append(SavedDraft(session_id, revision, draft, scheduled, reason, start))
            self.plans[program_id] = plan_text(scheduled)
            self.saved[(session_id, revision)] = DraftSaved(
                program_id,
                revision + 1,
                len(scheduled.weeks),
                sum(w.load_minutes for w in scheduled.weeks),
                list(scheduled.skipped_modules),
                scheduled.moved_tasks,
            )
        if self.block_after_save:
            await asyncio.Event().wait()
        return self.saved[(session_id, revision)]

    async def validate(self, user_id: str, session_id: str, program_id: str) -> None:
        owned = any(owner == user_id for owner, _ in self.goals)
        if self.programs.get(session_id) != program_id or not owned:
            raise AppError("program_not_found", "Programme introuvable.", 404)
        self.validate_calls += 1
        if program_id not in self.validated:
            self.validated.append(program_id)
        if self.block_after_validate:
            await asyncio.Event().wait()
