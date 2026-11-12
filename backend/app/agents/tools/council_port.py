"""Port du Conseil d'apprentissage (D84). `app.agents` n'importe aucune feature (contrat 6) : il
décrit ici ce dont le parcours `learning_council` a besoin (l'objectif, le cadrage, les tableaux,
les propositions, le choix) ; la composition branchera l'implémentation de la feature
`learning`, comme pour la mémoire (D68) et la recherche web (D77).

Chaque écriture est idempotente : un nœud rejoué après un arrêt (SPEC 9.4) réécrit la même
chose, jamais une ligne de plus.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.payloads import BoardKind
from app.core.errors import AppError

_Item = Annotated[str, Field(min_length=1, max_length=120)]
_Tradeoff = Annotated[str, Field(min_length=1, max_length=300)]


@dataclass(frozen=True)
class GoalBrief:
    """L'objectif tel que January l'a saisi (texte libre, poste visé, échéance, budget)."""

    goal_id: str
    text: str
    target_role: str | None
    deadline: date | None
    weekly_minutes: int | None
    framing: Mapping[str, str]  # réponses de cadrage déjà enregistrées, par id de question


@dataclass(frozen=True)
class FramingQuestion:
    id: str  # `q1` à `q5`, imposé par le code
    question: str


class ProposalDraft(BaseModel):
    """Un parcours proposé (SPEC 3.1, étape 5) : sortie structurée du Stratège (tâche 4.4)."""

    name: str = Field(min_length=3, max_length=80)
    promise: str = Field(min_length=10, max_length=300)
    duration_weeks: int = Field(ge=1, le=52)
    weekly_hours: int = Field(ge=1, le=40)
    skills: list[_Item] = Field(min_length=1, max_length=15)
    final_project: str = Field(min_length=10, max_length=400)
    tradeoffs: list[_Tradeoff] = Field(min_length=1, max_length=5)


@dataclass(frozen=True)
class ProposalRef:
    proposal_id: str
    rank: int
    name: str


@dataclass(frozen=True)
class SavedProposal:
    """Une proposition d'un lot déjà enregistré, avec ses détails tels qu'écrits (D85)."""

    ref: ProposalRef
    draft: ProposalDraft


@dataclass(frozen=True)
class Choice:
    """Le choix de January : un parcours (`choose`, un id) ou un mélange de deux (`mix`)."""

    action: Literal["choose", "mix"]
    proposal_ids: tuple[str, ...]
    start_date: date | None = None


class CouncilStore(Protocol):
    async def goal(self, user_id: str, goal_id: str) -> GoalBrief:
        """L'objectif de l'utilisateur ; `goal_not_found` (404) s'il n'est pas à lui."""
        ...

    async def save_framing(
        self,
        user_id: str,
        goal_id: str,
        questions: Sequence[FramingQuestion],
        answers: Mapping[str, str],
    ) -> None:
        """Questions et réponses du cadrage : écrase les précédentes (idempotent)."""
        ...

    async def save_board(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        step: int,
        kind: BoardKind,
        title: str,
        mermaid: str,
    ) -> str:
        """Un état du tableau du Scribe ; idempotent par `(session, step)`. Rend son id."""
        ...

    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None:
        """Compte rendu du Scribe (écrase le précédent)."""
        ...

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        batch: int,
        proposals: Sequence[ProposalDraft],
    ) -> list[ProposalRef]:
        """Un lot de propositions ; idempotent par `(session, batch)` : rejoué, rend le lot
        déjà écrit."""
        ...

    async def saved_proposals(
        self, user_id: str, session_id: str, *, batch: int
    ) -> list[SavedProposal]:
        """Le lot `batch` de la session tel qu'enregistré, par rang ; vide s'il n'existe pas. Un
        `propose` rejoué le relit au lieu de rappeler le modèle (D85)."""
        ...

    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None: ...

    async def record_choice(
        self, user_id: str, session_id: str, goal_id: str, choice: Choice
    ) -> None:
        """Marque le choix (une proposition choisie par lot au plus) ; idempotent."""
        ...

    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str:
        """Lance la session `program_builder` (une seule par objectif) ; rend son id."""
        ...


def council_unavailable() -> AppError:
    return AppError("council_unavailable", "Le Conseil n'est pas branché sur ce moteur.", 503)


class _NoCouncil:
    """Valeur par défaut du moteur (tests existants, démarrages sans le Conseil)."""

    async def goal(self, user_id: str, goal_id: str) -> GoalBrief:
        raise council_unavailable()

    async def save_framing(
        self,
        user_id: str,
        goal_id: str,
        questions: Sequence[FramingQuestion],
        answers: Mapping[str, str],
    ) -> None:
        raise council_unavailable()

    async def save_board(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        step: int,
        kind: BoardKind,
        title: str,
        mermaid: str,
    ) -> str:
        raise council_unavailable()

    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None:
        raise council_unavailable()

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        batch: int,
        proposals: Sequence[ProposalDraft],
    ) -> list[ProposalRef]:
        raise council_unavailable()

    async def saved_proposals(
        self, user_id: str, session_id: str, *, batch: int
    ) -> list[SavedProposal]:
        raise council_unavailable()

    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None:
        raise council_unavailable()

    async def record_choice(
        self, user_id: str, session_id: str, goal_id: str, choice: Choice
    ) -> None:
        raise council_unavailable()

    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str:
        raise council_unavailable()


NO_COUNCIL: CouncilStore = _NoCouncil()
