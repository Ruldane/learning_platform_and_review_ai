from typing import Any, Literal, Protocol, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.tools.conversation_port import TRAINING_TUTOR, TURN_TOKEN_LIMIT
from app.agents.tools.feynman_port import FeynmanAssessment, FeynmanExchange
from app.core.errors import AppError
from app.providers.llm.limits import with_output_limit

FIRST_QUESTION = "Peux-tu m’expliquer le sujet avec tes mots et me donner un exemple ?"
MAX_REPLY = 2000


class FeynmanState(TypedDict, total=False):
    thread_id: str
    turn_id: str
    summary: str
    feynman: bool
    explanation: str | None
    follow_up: str | None
    clarification: str | None
    assessment: dict[str, Any]


class FeynmanNode(Protocol):
    async def __call__(self, state: FeynmanState) -> FeynmanState: ...


def _ask(question: str) -> str | None:
    response = interrupt(
        {
            "kind": "feynman_explanation",
            "question": question,
            "fields": [
                {
                    "id": "answer",
                    "label": "Ton explication",
                    "required": True,
                    "max_length": MAX_REPLY,
                }
            ],
        }
    )
    fields = response.get("answers") if isinstance(response, dict) else None
    answer = fields.get("answer") if isinstance(fields, dict) else None
    return answer.strip()[:MAX_REPLY] or None if isinstance(answer, str) else None


def ask_explanation(state: FeynmanState) -> FeynmanState:
    return {"explanation": _ask(FIRST_QUESTION)}


def ask_clarification(state: FeynmanState) -> FeynmanState:
    return {"clarification": _ask(state["follow_up"] or FIRST_QUESTION)}


def explained(state: FeynmanState) -> bool:
    return state.get("explanation") is not None


def clarified(state: FeynmanState) -> bool:
    return state.get("clarification") is not None


def assess_next(state: FeynmanState) -> Literal["clarify", "save_feynman"]:
    return "clarify" if state.get("follow_up") else "save_feynman"


def make_assessment(deps: GraphDeps, *, final: bool) -> FeynmanNode:
    @node_timeout()
    async def assess(state: FeynmanState) -> FeynmanState:
        context = await deps.ports.conversations.feynman_context(
            deps.user_id, deps.session_id, state["thread_id"], state["turn_id"]
        )
        if context is None:
            return {"follow_up": None}
        text = [
            "Référence : "
            + untrusted(_fitted(context.title + "\n" + context.material, 2300), "source"),
            "Explication : "
            + untrusted(_fitted(state.get("explanation") or "", 1000), "explication"),
        ]
        if final:
            exchange = (state.get("follow_up") or "") + "\n" + (state.get("clarification") or "")
            text.append("Dernière réponse : " + untrusted(_fitted(exchange, 1200), "relance"))
        text.append("Aucune nouvelle relance." if final else "Une relance est possible.")
        prompt = render_prompt("feynman")
        cap = min(TURN_TOKEN_LIMIT, deps.settings.session_token_cap)
        room = cap - context.used_tokens - len((prompt + "\n".join(text)).encode()) - 1900
        if room < 300:
            raise AppError(
                "conversation_budget_reached", "Le budget de cet échange est atteint.", 429
            )
        model = await deps.models.get_chat_model(
            deps.user_id, "fort" if context.strong else "rapide", agent=TRAINING_TUTOR
        )
        assessment = await structured_call(
            with_output_limit(model, min(room, 850)),
            FeynmanAssessment,
            [SystemMessage(prompt), HumanMessage("\n\n".join(text))],
            agent=TRAINING_TUTOR,
            step="feynman_bilan" if final else "feynman_ecoute",
            intent="J’identifie les points à éclaircir dans l’explication.",
            retries=0,
        )
        result: FeynmanState = {"assessment": assessment.model_dump(mode="json")}
        if not final:
            result["follow_up"] = assessment.follow_up
        return result

    return assess


def _fitted(text: str, size: int) -> str:
    return text.encode()[:size].decode(errors="ignore")


def make_save_feynman(deps: GraphDeps) -> FeynmanNode:
    async def save(state: FeynmanState) -> FeynmanState:
        if result := state.get("assessment"):
            await deps.ports.conversations.save_feynman(
                deps.user_id,
                deps.session_id,
                state["thread_id"],
                state["turn_id"],
                assessment=FeynmanAssessment.model_validate(result),
                exchange=FeynmanExchange.model_validate(state),
            )
        return {"summary": "Bilan de l’explication enregistré."}

    return save
