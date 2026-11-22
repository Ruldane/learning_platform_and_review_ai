"""La question posée à January et la lecture de sa réponse (SPEC F10, 9.4, D145).

`ask` ne fait qu'`interrupt()` puis relit la réponse (pur, sans port ni modèle) : seul dans son
nœud, rejoué depuis son début à la reprise, il repose la même question, celle de l'état.

Question (`kind = "interview_answer"`) : `question` est le texte posé (la question principale, ou
sa relance) ; `fields` un champ texte `answer` (4 000 caractères) ; `options` une seule, `stop`
(« Terminer l'entretien »). Réponse : `{"answers": {"answer": texte}}`, ou `"stop"` (ou
`{"action": "stop"}`). Une réponse illisible (texte vide, forme inconnue) repose la même question.

`turn` lit la réponse (dans `untrusted`) : une note interne de 1 à 5 et, au plus une fois par
question, une relance qui repasse par `ask`. Un modèle muet ou trop lent (`RECOVERABLE_CODES`) ne
fait pas échouer l'entretien : note neutre, pas de relance. Les échanges restent dans l'état
jusqu'à `save`."""

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.nodes.interviewer.common import (
    AGENT,
    RECOVERABLE_CODES,
    Node,
    context_of,
    say_question,
)
from app.agents.nodes.interviewer.context import exchange_text, head_vars
from app.agents.nodes.interviewer.salary import salary_decision
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import (
    Exchange,
    InterviewContext,
    PlannedQuestion,
    TurnDecision,
)
from app.core.errors import AppError

KIND = "interview_answer"
STOP = "stop"
STOP_LABEL = "Terminer l'entretien"
ANSWER_FIELD = {"id": "answer", "label": "Ta réponse", "required": True, "max_length": 4000}
MAX_ANSWER_CHARS = 4000
TURN_REQUEST = "Lis la réponse et note-la."
TURN_CALL_TIMEOUT_S = 105.0  # plus court que le plafond d'un nœud (120 s) : le repli s'écrit
NEUTRAL_NOTE = 3
CRITERION_LABELS = {
    "clarte": "clarté",
    "structure": "structure",
    "profondeur": "profondeur technique",
    "adequation": "adéquation au poste",
}

logger = logging.getLogger(__name__)


def question_payload(state: InterviewState) -> dict[str, Any]:
    return {
        "kind": KIND,
        "question": state["current"],
        "options": [{"value": STOP, "label": STOP_LABEL}],
        "fields": [ANSWER_FIELD],
    }


def parse_reply(value: Any) -> dict[str, Any] | None:
    """`{"action": "answer", "text"}`, `{"action": "stop"}` ou `None` (la question est reposée)."""
    if value == STOP or (isinstance(value, dict) and value.get("action") == STOP):
        return {"action": STOP}
    answers = value.get("answers") if isinstance(value, dict) else None
    text = answers.get("answer") if isinstance(answers, dict) else None
    if isinstance(text, str) and text.strip():
        return {"action": "answer", "text": text.strip()[:MAX_ANSWER_CHARS]}
    return None


def ask(state: InterviewState) -> InterviewState:
    """Point d'arrêt : la question en cours. Rien avant `interrupt()`."""
    return {"reply": parse_reply(interrupt(question_payload(state)))}


def route_ask(state: InterviewState) -> str:
    reply = state.get("reply")
    if reply is None:
        return "ask"
    return "debrief" if reply["action"] == STOP else "turn"


def route_turn(state: InterviewState) -> str:
    """Une question reste à poser (la relance, ou la suivante), sinon le débrief."""
    return "debrief" if state["position"] >= len(state["plan"]) else "ask"


def _previous(state: InterviewState) -> str:
    """L'échange de la question en cours jusqu'à sa relance (celle-ci attend sa note)."""
    last = Exchange.model_validate(state["exchanges"][-1])
    return untrusted(
        exchange_text(last, with_note=False, pending_follow_up=True), "échange précédent"
    )


def turn_vars(
    ctx: InterviewContext, planned: PlannedQuestion, state: InterviewState, text: str
) -> dict[str, Any]:
    final = state["follow_up_open"]
    return {
        **head_vars(ctx),
        "mode": "turn",
        "final": final,
        "criterion_label": CRITERION_LABELS[planned.criterion],
        "question": untrusted(planned.text, "question de l'entretien"),
        "answer": untrusted(text, "réponse de January"),
        "before": _previous(state) if final else "",
    }


async def _decide(
    deps: GraphDeps, state: InterviewState, planned: PlannedQuestion, text: str
) -> tuple[TurnDecision, bool]:
    """La décision du modèle, et si c'est un repli ; sans réponse lisible à temps : note neutre,
    pas de relance."""
    step = f"tour-{state['position'] + 1}" + ("-relance" if state["follow_up_open"] else "")
    prompt = render_prompt(AGENT, **turn_vars(context_of(state), planned, state, text))
    try:
        async with asyncio.timeout(TURN_CALL_TIMEOUT_S):
            model = await deps.models.get_chat_model(
                deps.user_id, get_agent(AGENT).tier, agent=AGENT
            )
            decision = await structured_call(
                model,
                TurnDecision,
                [SystemMessage(prompt), HumanMessage(TURN_REQUEST)],
                agent=AGENT,
                step=step,
                intent="je lis ta réponse",
            )
            return decision, False
    except (AppError, TimeoutError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        if code != "timeout" and code not in RECOVERABLE_CODES:
            raise
        logger.warning(
            "Intervieweur sans réponse du modèle (%s), note neutre : session %s, %s",
            code,
            deps.session_id,
            step,
        )
        return TurnDecision(follow_up=None, note=NEUTRAL_NOTE), True


def _answered(
    state: InterviewState,
    planned: PlannedQuestion,
    text: str,
    decision: TurnDecision,
    fallback: bool,
) -> list[dict[str, Any]]:
    """Les échanges avec cette réponse : la relance répondue complète le dernier échange (en repli,
    la note de la première réponse reste) ; sinon un nouvel échange (la relance, s'il y en a une,
    attend sa réponse)."""
    exchanges = list(state["exchanges"])
    if state["follow_up_open"]:
        last = {**exchanges[-1], "follow_up_answer": text}
        if not fallback:
            last["note"] = decision.note
        return [*exchanges[:-1], last]
    exchange = Exchange(
        index=state["position"],
        question=planned.text,
        criterion=planned.criterion,
        source=planned.source,
        answer=text,
        follow_up=decision.follow_up,
        note=decision.note,
        unrated=fallback,
        salary_raised=decision.salary_move,
    )
    return [*exchanges, exchange.model_dump()]


def make_turn(deps: GraphDeps) -> Node:
    @node_timeout()
    async def turn(state: InterviewState) -> InterviewState:
        """Note la réponse ; une relance au plus par question, sinon la question suivante."""
        reply = state["reply"]
        if reply is None or reply["action"] != "answer":  # `route_ask` ne l'envoie pas ici
            raise RuntimeError("`turn` demande une réponse lue par `ask`")
        planned = PlannedQuestion.model_validate(state["plan"][state["position"]])
        decision, fallback = await _decide(deps, state, planned, reply["text"])
        context = context_of(state)
        decision = salary_decision(state, context, decision)
        if context.surprise:
            decision = decision.model_copy(update={"follow_up": None})
        exchanges = _answered(state, planned, reply["text"], decision, fallback)
        position = state["position"]
        logger.info("Réponse notée : session %s, question %d", deps.session_id, position + 1)
        if not state["follow_up_open"] and decision.follow_up:
            say_question(position + 1, decision.follow_up, follow_up=True)
            return {"exchanges": exchanges, "current": decision.follow_up, "follow_up_open": True}
        position += 1
        current = ""
        if position < len(state["plan"]):
            current = state["plan"][position]["text"]
            say_question(position + 1, current)
        return {
            "exchanges": exchanges,
            "position": position,
            "current": current,
            "follow_up_open": False,
        }

    return turn
