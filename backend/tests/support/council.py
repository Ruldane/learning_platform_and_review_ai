"""Faux port du Conseil (`CouncilStore`) en mémoire, idempotent comme le contrat : un nœud rejoué
réécrit la même chose sans ligne de plus. Sert aux tests du parcours `learning_council`."""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from uuid import uuid4

from app.agents.runtime.payloads import BoardKind
from app.agents.tools.council_port import (
    Choice,
    FramingQuestion,
    GoalBrief,
    ProposalDraft,
    ProposalRef,
)
from app.core.errors import AppError

GOAL_ID = "11111111-2222-3333-4444-555555555555"
GOAL_TEXT = "Devenir AI product engineer"


def goal_not_found() -> AppError:
    return AppError("goal_not_found", "Objectif introuvable.", 404)


@dataclass
class FakeCouncilStore:
    """`goals` : (utilisateur, objectif) → brief. `framing_saved` ne garde que les écritures qui
        changent quelque chose (une réécriture à l'identique n'en ajoute pas) ; `framing_calls`
        compte tous les appels. `block_after_framing` : fige l'appel après l'écriture (arrêt du back
        en plein nœud). `boards` : id par `(session, étape)`, `board_kinds` leur type ; `choices` :
        les choix enregistrés (un seul par session et objectif), `programs_started` : les sessions
        `program_builder` lancées (une seule par objectif). Chaque écriture vérifie que l'objectif
    (ou la proposition) est à l'utilisateur : un oubli du filtre utilisateur échoue (404)."""

    goals: dict[tuple[str, str], GoalBrief] = field(default_factory=dict)
    framing: dict[tuple[str, str], tuple[list[dict[str, str]], dict[str, str]]] = field(
        default_factory=dict
    )
    framing_saved: list[tuple[list[dict[str, str]], dict[str, str]]] = field(default_factory=list)
    framing_calls: int = 0
    block_after_framing: bool = False
    boards: dict[tuple[str, int], str] = field(default_factory=dict)
    board_kinds: dict[tuple[str, int], BoardKind] = field(default_factory=dict)
    minutes: dict[str, str] = field(default_factory=dict)
    batches: dict[tuple[str, int], list[ProposalRef]] = field(default_factory=dict)
    attached: dict[str, str] = field(default_factory=dict)
    chosen: dict[tuple[str, str], Choice] = field(default_factory=dict)
    choices: list[Choice] = field(default_factory=list)
    programs: dict[str, str] = field(default_factory=dict)
    programs_started: int = 0
    owners: dict[str, str] = field(default_factory=dict)  # proposition → utilisateur

    def add_goal(
        self,
        user_id: str,
        *,
        goal_id: str = GOAL_ID,
        text: str = GOAL_TEXT,
        target_role: str | None = "AI product engineer",
        deadline: date | None = None,
        weekly_minutes: int | None = 600,
    ) -> GoalBrief:
        brief = GoalBrief(goal_id, text, target_role, deadline, weekly_minutes, {})
        self.goals[(user_id, goal_id)] = brief
        return brief

    async def goal(self, user_id: str, goal_id: str) -> GoalBrief:
        brief = self.goals.get((user_id, goal_id))
        if brief is None:
            raise goal_not_found()
        return brief

    async def save_framing(
        self,
        user_id: str,
        goal_id: str,
        questions: Sequence[FramingQuestion],
        answers: Mapping[str, str],
    ) -> None:
        await self.goal(user_id, goal_id)
        self.framing_calls += 1
        value = ([{"id": q.id, "question": q.question} for q in questions], dict(answers))
        if self.framing.get((user_id, goal_id)) != value:
            self.framing[(user_id, goal_id)] = value
            self.framing_saved.append(value)
        if self.block_after_framing:
            await asyncio.Event().wait()

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
        await self.goal(user_id, goal_id)  # un oubli du filtre utilisateur échoue (404)
        self.board_kinds.setdefault((session_id, step), kind)
        return self.boards.setdefault((session_id, step), uuid4().hex)

    async def save_minutes(self, user_id: str, goal_id: str, text: str) -> None:
        await self.goal(user_id, goal_id)
        self.minutes[goal_id] = text

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        goal_id: str,
        *,
        batch: int,
        proposals: Sequence[ProposalDraft],
    ) -> list[ProposalRef]:
        await self.goal(user_id, goal_id)
        refs = [ProposalRef(uuid4().hex, rank, p.name) for rank, p in enumerate(proposals, 1)]
        kept = self.batches.setdefault((session_id, batch), refs)
        self.owners.update({ref.proposal_id: user_id for ref in kept})
        return list(kept)

    async def attach_board(self, user_id: str, proposal_id: str, board_id: str) -> None:
        if self.owners.get(proposal_id) != user_id:
            raise AppError("proposal_not_found", "Proposition introuvable.", 404)
        self.attached[proposal_id] = board_id

    async def record_choice(
        self, user_id: str, session_id: str, goal_id: str, choice: Choice
    ) -> None:
        await self.goal(user_id, goal_id)
        if (session_id, goal_id) not in self.chosen:
            self.chosen[(session_id, goal_id)] = choice
            self.choices.append(choice)

    async def start_program(self, user_id: str, goal_id: str, choice: Choice) -> str:
        await self.goal(user_id, goal_id)
        if goal_id not in self.programs:
            self.programs[goal_id] = uuid4().hex
            self.programs_started += 1
        return self.programs[goal_id]
