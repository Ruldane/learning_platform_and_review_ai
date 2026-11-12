"""Le Scribe (SPEC 3.3, 9.1, D85) : dessine au tableau en Mermaid `flowchart` (jamais de
coordonnées) et tient le compte rendu. Il ne prend pas position.

Le Mermaid est filtré par le code (`mermaid_rules`) : refusé, une nouvelle demande ; encore
refusé (ou sortie invalide), aucun tableau, le Conseil continue (journal : identifiants). Chaque
tableau a son numéro d'étape, tiré de `board_step` de l'état d'entrée : un nœud rejoué réécrit les
mêmes étapes, que le port enregistre une seule fois (idempotent par session et étape)."""

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.nodes.council_rules import (
    MINUTES_WORDS,
    Node,
    citation_entries,
    goal_vars,
    notes_prompt,
    transcript_prompt,
)
from app.agents.nodes.mermaid_rules import (
    MAX_LABEL_CHARS,
    MAX_MERMAID_LINES,
    MAX_NODES,
    mermaid_problems,
)
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.events import BoardKind
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.speech import speak
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState
from app.core.errors import AppError

AGENT = "scribe"
INVALID_OUTPUT_CODE = "structured_output_invalid"
BOARDS_TIMEOUT_S = 300  # une frise par proposition et une comparaison, deux essais chacune
_FENCE = re.compile(r"^```[a-z]*\s*\n|\n?```\s*$")

logger = logging.getLogger(__name__)


class BoardDraft(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    mermaid: str = Field(min_length=10, max_length=6000)


def _clean(code: str) -> str:
    """Retire une éventuelle balise de code autour du schéma."""
    return _FENCE.sub("", code.strip()).strip()


def _board_prompt(state: CouncilState, kind: BoardKind, brief: str) -> str:
    return render_prompt(
        AGENT,
        mode="board",
        kind=kind,
        **goal_vars(state),
        brief=brief,
        max_lines=MAX_MERMAID_LINES,
        max_nodes=MAX_NODES,
        max_label=MAX_LABEL_CHARS,
    )


async def _valid_draft(
    deps: GraphDeps, messages: list[BaseMessage], step: int
) -> BoardDraft | None:
    """Un schéma qui passe le filtre, en deux demandes au plus ; sinon `None`."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    for attempt in range(2):
        try:
            draft = await structured_call(
                model,
                BoardDraft,
                messages,
                agent=AGENT,
                step=f"tableau-{step}",
                intent="je dessine au tableau",
            )
        except AppError as exc:
            if exc.code != INVALID_OUTPUT_CODE:
                raise
            return None
        draft = BoardDraft(title=" ".join(draft.title.split()), mermaid=_clean(draft.mermaid))
        problems = mermaid_problems(draft.mermaid)
        if not problems:
            return draft
        if attempt == 0:
            refused = "\n".join(f"- {problem}" for problem in problems)
            messages = [
                *messages,
                AIMessage(json.dumps(draft.model_dump(), ensure_ascii=False)),
                HumanMessage(f"Schéma refusé :\n{refused}\nRedessine-le en respectant les règles."),
            ]
    return None


async def draw(
    deps: GraphDeps, state: CouncilState, *, kind: BoardKind, step: int, brief: str
) -> str | None:
    """Dessine un tableau, l'enregistre (idempotent) puis publie `board.update` ; rend son id, ou
    `None` si aucun schéma valable n'a été obtenu."""
    messages: list[BaseMessage] = [
        SystemMessage(_board_prompt(state, kind, brief)),
        HumanMessage("Dessine le tableau."),
    ]
    draft = await _valid_draft(deps, messages, step)
    if draft is None:
        logger.warning(
            "Tableau non dessiné (%s) : session %s, étape %d", kind, deps.session_id, step
        )
        return None
    board_id = await deps.ports.council.save_board(
        deps.user_id,
        deps.session_id,
        state["goal_id"],
        step=step,
        kind=kind,
        title=draft.title,
        mermaid=draft.mermaid,
    )
    emit(
        "board.update",
        {
            "mermaid": draft.mermaid,
            "step": step,
            "board_id": board_id,
            "kind": kind,
            "title": draft.title,
        },
        agent=AGENT,
    )
    return board_id


def make_domain_map(deps: GraphDeps) -> Node:
    @node_timeout()
    async def domain_map(state: CouncilState) -> CouncilState:
        """Carte du domaine, d'après les positions du tour 1."""
        step = state.get("board_step", 0) + 1
        positions = [t for t in state.get("turns", []) if t["round"] == 1]
        await draw(deps, state, kind="domain_map", step=step, brief=transcript_prompt(positions))
        return {"board_step": step}

    return domain_map


def make_prerequisites(deps: GraphDeps) -> Node:
    @node_timeout()
    async def prerequisites(state: CouncilState) -> CouncilState:
        """Graphe des prérequis, d'après tout le débat."""
        step = state.get("board_step", 0) + 1
        brief = transcript_prompt(state.get("turns", []))
        await draw(deps, state, kind="prerequisites", step=step, brief=brief)
        return {"board_step": step}

    return prerequisites


def make_minutes(deps: GraphDeps) -> Node:
    @node_timeout()
    async def minutes(state: CouncilState) -> CouncilState:
        """Compte rendu (200 mots au plus, cité), gardé sur l'objectif pour le Stratège."""
        prompt = render_prompt(
            AGENT,
            mode="minutes",
            **goal_vars(state),
            transcript=transcript_prompt(state.get("turns", [])),
            notes=notes_prompt(state.get("notes", [])),
            max_words=MINUTES_WORDS,
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        spoken = await speak(
            model,
            [SystemMessage(prompt), HumanMessage("Rédige le compte rendu.")],
            agent=AGENT,
            step=f"compte-rendu-{state.get('round', 1)}",
            intent="je rédige le compte rendu",
            catalog=citation_entries(state),
            max_words=MINUTES_WORDS,
        )
        await deps.ports.council.save_minutes(deps.user_id, state["goal_id"], spoken.text)
        return {"minutes": spoken.text}

    return minutes


def _proposal_lines(proposal: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Nom : {proposal['name']}",
            f"Promesse : {proposal.get('promise', '')}",
            f"Durée : {proposal.get('duration_weeks', '?')} semaines, "
            f"{proposal.get('weekly_hours', '?')} h par semaine",
            f"Compétences : {', '.join(proposal.get('skills', []))}",
            f"Projet final : {proposal.get('final_project', '')}",
            f"Compromis : {' ; '.join(proposal.get('tradeoffs', []))}",
        ]
    )


def _proposal_brief(proposal: dict[str, Any]) -> str:
    return untrusted(_proposal_lines(proposal), f"proposition {proposal['rank']}")


def make_proposal_boards(deps: GraphDeps) -> Node:
    @node_timeout(BOARDS_TIMEOUT_S)
    async def proposal_boards(state: CouncilState) -> CouncilState:
        """Une frise par proposition (rattachée à elle), puis la comparaison du lot."""
        proposals = state.get("proposals", [])
        step = state.get("board_step", 0)
        for proposal in proposals:
            step += 1
            board_id = await draw(
                deps, state, kind="timeline", step=step, brief=_proposal_brief(proposal)
            )
            if board_id is not None:
                await deps.ports.council.attach_board(
                    deps.user_id, proposal["proposal_id"], board_id
                )
        step += 1
        brief = "\n\n".join(_proposal_brief(p) for p in proposals)
        await draw(deps, state, kind="comparison", step=step, brief=brief)
        return {"board_step": step}

    return proposal_boards
