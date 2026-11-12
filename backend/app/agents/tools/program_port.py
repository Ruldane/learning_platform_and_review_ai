"""Port du programme (D86). `app.agents` n'importe aucune feature (contrat 6) : il décrit ici ce
dont le parcours `program_builder` a besoin (le contexte du Stratège, les règles de planification,
l'enregistrement d'un brouillon, la validation) ; la feature `program` l'implémente (tâche 4.7).

Les règles de SPEC 3.4 (85 % du budget, acquis, pratique et quiz chaque semaine) vivent dans la
feature (`check_draft`, `schedule`) et sont appelées par le port : un seul jeu de règles pour le
Stratège et pour les modifications de January. Le plan est en base, pas dans l'état du graphe :
une révision relit le plan courant, modifications de January comprises (`current_plan`).

Chaque écriture est idempotente : un nœud rejoué après un arrêt (SPEC 9.4) réécrit la même chose,
jamais une ligne de plus.
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
    """Le budget d'une semaine tel que le Stratège doit le respecter (minutes)."""

    weekly_minutes: int
    cap_minutes: int  # 85 % du budget hebdomadaire
    weekday_minutes: int  # lundi à vendredi, chacun
    weekend_minutes: int  # le bloc du samedi ; dimanche libre


@dataclass(frozen=True)
class ProgramContext:
    goal: GoalBrief
    proposals: list[ProposalDraft]  # une (parcours choisi) ou deux (mélange)
    budget: BudgetView
    known_skills: KnownSkills
    language: str  # langue des leçons
    council_minutes: str | None  # compte rendu du Scribe
    # Plan courant en texte (modifications de January comprises), pour une révision.
    current_plan: str | None


@dataclass(frozen=True)
class DraftSaved:
    program_id: str
    version: int
    weeks: int
    total_minutes: int
    skipped_modules: list[str]  # modules sautés car déjà acquis
    moved_tasks: int  # tâches reportées à une semaine suivante par l'ordonnancement


class ProgramStore(Protocol):
    async def context(
        self, user_id: str, goal_id: str, proposal_ids: Sequence[str], program_id: str | None
    ) -> ProgramContext:
        """Objectif, propositions choisies, budget, acquis, langue, compte rendu ; avec
        `program_id`, le plan courant en texte. `goal_not_found` / `proposal_not_found` (404)."""
        ...

    async def check_draft(self, user_id: str, goal_id: str, draft: PlanDraft) -> list[str]:
        """Problèmes du brouillon (phrases françaises), selon le budget de l'utilisateur."""
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
        """Range le brouillon (acquis, 85 %, pratique et quiz) et l'enregistre ; idempotent par
        `(session, revision)` : revision 0 crée le programme, les suivantes une version.
        `planning_impossible` (422) si le budget ne permet aucune semaine."""
        ...

    async def validate(self, user_id: str, session_id: str, program_id: str) -> None:
        """Valide le programme (idempotent)."""
        ...


def program_unavailable() -> AppError:
    return AppError("program_unavailable", "Le programme n'est pas branché sur ce moteur.", 503)


class _NoProgram:
    """Valeur par défaut du moteur (tests existants, démarrages sans la feature `program`)."""

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
