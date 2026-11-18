"""Le professeur (10.A3) : un seul nœud, un seul appel de modèle par déclenchement, une sortie
structurée (`TeacherNote`) rangée par le port (`IdeStore.save_note`, donc par le service que Claude
utilise aussi : seul l'auteur change).

Le niveau de modèle suit le type de note (`plan_of`) : léger pour un indice ou une annotation, fort
pour une explication ou une proposition. Le contexte est borné par le code (`build_context`). Le
début du prompt est fixe et marqué pour le cache. Journal : l'identifiant de séance, le modèle et
les jetons de l'appel, jamais un texte (code, question, réponse : SPEC 17.2)."""

import logging

from langchain_core.messages import BaseMessage

from app.agents.nodes.professor.context import build_context
from app.agents.nodes.professor.plan import Trigger, plan_of
from app.agents.nodes.professor.prompt import AGENT, prefix_of, turn_of
from app.agents.nodes.professor.rules import finish
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.repositories import LlmCallRepository
from app.agents.runtime.structured import structured_call
from app.agents.state.ide_teacher import IdeTeacherState, Node
from app.agents.tools.ide_schema import TeacherNote

__all__ = ["AGENT", "SUMMARY_SAVED", "SUMMARY_STALE", "make_teach"]

SUMMARY_SAVED = "Note du professeur rangée."
SUMMARY_STALE = "Le code a changé pendant la réponse : repose la question."
SUMMARY_NONE = "Rien à dire : le code est réussi."
INTENTS = {
    "hint": "j'écris un indice",
    "annotation": "j'annote la marge",
    "explanation": "j'explique",
    "proposal": "j'explique ou je propose",
}

logger = logging.getLogger(__name__)


async def _log_usage(deps: GraphDeps, ide_session_id: str) -> None:
    """Une ligne par appel : la séance de code, le modèle et les jetons (rien d'autre)."""
    async with deps.session_factory() as db:
        model, tokens = await LlmCallRepository(db, deps.user_id).usage_of_session(deps.session_id)
    logger.info("Professeur : séance %s, modèle %s, %d jetons", ide_session_id, model, tokens)


def make_teach(deps: GraphDeps) -> Node:
    @node_timeout(150)
    async def teach(state: IdeTeacherState) -> IdeTeacherState:
        trigger: Trigger = state["trigger"]  # type: ignore[assignment]  # validé par l'entrée
        if trigger == "run_ok":  # jamais d'appel : au plus un compliment, rangé par la route
            return {"summary": SUMMARY_NONE}
        ide_session_id = state["ide_session_id"]
        ports = deps.ports.ide
        inputs = await ports.teacher_inputs(deps.user_id, ide_session_id, state.get("run_id"))
        plan = plan_of(trigger, inputs.style)
        ctx = build_context(
            inputs,
            file_path=state.get("file_path"),
            cursor_line=state.get("line"),
            question=state.get("question"),
        )
        level = state.get("level") or 1
        messages: list[BaseMessage] = [
            prefix_of(inputs),
            turn_of(
                inputs, plan, ctx, trigger=trigger, level=level, question=state.get("question")
            ),
        ]
        model = await deps.models.get_chat_model(deps.user_id, plan.tier, agent=AGENT)
        raw = await structured_call(
            model,
            TeacherNote,
            messages,
            agent=AGENT,
            step="reponse",
            intent=INTENTS[plan.kind if len(plan.kinds) == 1 else "proposal"],
        )
        await _log_usage(deps, ide_session_id)
        note, base_hash = finish(raw, plan, inputs, ctx, level)
        saved = await ports.save_note(
            deps.user_id,
            ide_session_id,
            note,
            base_hash=base_hash,
            error_key=state.get("error_key"),
        )
        return {"summary": SUMMARY_SAVED if saved else SUMMARY_STALE}

    return teach
