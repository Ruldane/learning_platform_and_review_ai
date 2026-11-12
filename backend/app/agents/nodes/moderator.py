"""Le Modérateur du Conseil (SPEC 3.1, 9.1) : lit l'objectif et la mémoire, prépare 5 questions
de cadrage au plus, s'arrête pour les poser (point d'arrêt n° 1), puis enregistre les réponses
et prépare la demande de l'Éclaireur.

L'arrêt vit seul dans `ask_framing` : aucun effet de bord avant `interrupt()` (SPEC 9.4).
L'écriture des réponses a lieu dans le nœud suivant, idempotente (le port écrase).

Objectif, poste visé et réponses viennent de January : non encadrés dans les prompts (D53 §5),
jamais journalisés (17.2)."""

from datetime import date
from typing import Any, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.agents.nodes.memory_context import load_memory_context
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState
from app.agents.tools.council_port import FramingQuestion, GoalBrief

AGENT = "moderator"
MAX_FRAMING_QUESTIONS = 5
MAX_ANSWER_CHARS = 2000
MAX_QUERY_CHARS = 300
FRAMING_PROMPT = "Réponds aux questions de cadrage (facultatif), puis lance la recherche."
GO = {"value": "go", "label": "Lancer la recherche"}


class Node(Protocol):
    async def __call__(self, state: CouncilState) -> CouncilState: ...


class FramingQuestionModel(BaseModel):
    question: str = Field(min_length=5, max_length=300)


class FramingPlan(BaseModel):
    questions: list[FramingQuestionModel] = Field(max_length=MAX_FRAMING_QUESTIONS)


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _goal_state(goal: GoalBrief) -> dict[str, Any]:
    return {
        "goal_id": goal.goal_id,
        "text": goal.text,
        "target_role": goal.target_role,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "weekly_minutes": goal.weekly_minutes,
        "framing": dict(goal.framing),
    }


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: CouncilState) -> CouncilState:
        """L'objectif (port du Conseil), puis le contexte mémoire proche de son texte."""
        goal = await deps.ports.council.goal(deps.user_id, state["goal_id"])
        memory = await load_memory_context(deps, objective=goal.text, agent=AGENT)
        return {"goal": _goal_state(goal), "context": memory.as_prompt()}

    return context


def _deadline(goal: dict[str, Any]) -> str:
    raw = goal.get("deadline")
    return date.fromisoformat(raw).strftime("%d/%m/%Y") if raw else "aucune"


def make_frame(deps: GraphDeps) -> Node:
    @node_timeout()
    async def frame(state: CouncilState) -> CouncilState:
        goal = state["goal"]
        prompt = render_prompt(
            AGENT,
            mode="frame",
            goal=goal["text"],
            target_role=goal.get("target_role") or "non précisé",
            deadline=_deadline(goal),
            weekly_minutes=goal.get("weekly_minutes"),
            context=state.get("context", ""),
            max_questions=MAX_FRAMING_QUESTIONS,
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        plan = await structured_call(
            model,
            FramingPlan,
            [SystemMessage(prompt), HumanMessage("Prépare les questions de cadrage.")],
            agent=AGENT,
            step="cadrage",
            intent="je prépare les questions de cadrage",
        )
        questions = [
            {"id": f"q{index}", "question": _one_line(item.question)}
            for index, item in enumerate(plan.questions[:MAX_FRAMING_QUESTIONS], start=1)
        ]
        return {"framing_questions": questions}

    return frame


def framing_answers(value: Any, ids: list[str]) -> dict[str, str]:
    """Réponses lues de la reprise : `{"answers": {id: texte}}` ; ids inconnus et réponses vides
    ignorés, chaque réponse coupée à 2 000 caractères. `"go"` ou toute autre forme : aucune."""
    raw = value.get("answers") if isinstance(value, dict) else None
    if not isinstance(raw, dict):
        return {}
    answers: dict[str, str] = {}
    for qid in ids:
        text = raw.get(qid)
        if isinstance(text, str) and text.strip():
            answers[qid] = text.strip()[:MAX_ANSWER_CHARS]
    return answers


def ask_framing(state: CouncilState) -> CouncilState:
    """Point d'arrêt n° 1 (fin du cadrage), obligatoire même sans question. Rien avant
    `interrupt()` : le nœud redémarre depuis son début à la reprise."""
    questions = state.get("framing_questions", [])
    value = interrupt(
        {
            "kind": "framing",
            "question": FRAMING_PROMPT,
            "options": [GO],
            "fields": [{"id": q["id"], "label": q["question"]} for q in questions],
        }
    )
    return {"framing_answers": framing_answers(value, [q["id"] for q in questions])}


def research_query(
    goal: dict[str, Any], questions: list[dict[str, str]], answers: dict[str, str]
) -> str:
    """Demande de l'Éclaireur : objectif, poste visé, puis réponses dans l'ordre des questions,
    sur une ligne, 300 caractères au plus."""
    parts = [goal["text"], goal.get("target_role") or ""]
    parts += [answers.get(q["id"], "") for q in questions]
    line = " ; ".join(clean for part in parts if (clean := _one_line(part)))
    return line[:MAX_QUERY_CHARS].rstrip(" ;")


def make_apply_framing(deps: GraphDeps) -> Node:
    @node_timeout()
    async def apply_framing(state: CouncilState) -> CouncilState:
        """Enregistre questions et réponses (le port écrase : rejoué, il réécrit la même chose),
        puis prépare la recherche."""
        questions = state.get("framing_questions", [])
        answers = state.get("framing_answers", {})
        await deps.ports.council.save_framing(
            deps.user_id,
            state["goal_id"],
            [FramingQuestion(q["id"], q["question"]) for q in questions],
            answers,
        )
        return {"query": research_query(state["goal"], questions, answers), "urls": []}

    return apply_framing
