"""The professor (10.A3): a single node, a single model call per trigger, a structured output
(`TeacherNote`) filed by the port (`IdeStore.save_note`, hence by the service that Claude also
uses: only the author changes).

The model tier follows the note type (`plan_of`): light for a hint or an annotation, strong for
an explanation or a proposal. The context is bounded by the code (`build_context`). The start of
the prompt is fixed and marked for the cache. Log: the session id, the model and the tokens of
the call, never a text (code, question, answer: SPEC 17.2)."""

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

SUMMARY_SAVED = "Professor's note saved."
SUMMARY_STALE = "Your code changed while the professor was replying. Ask your question again."
SUMMARY_NONE = "Your code passed its checks."
INTENTS = {
    "hint": "Writing a hint",
    "annotation": "Annotating the code",
    "explanation": "Preparing an explanation",
    "proposal": "Preparing an explanation or proposed fix",
}

logger = logging.getLogger(__name__)


async def _log_usage(deps: GraphDeps, ide_session_id: str) -> None:
    """Log one line per call with the IDE session ID, model, and token count."""
    async with deps.session_factory() as db:
        model, tokens = await LlmCallRepository(db, deps.user_id).usage_of_session(deps.session_id)
    logger.info("Professor session %s, model %s, %d tokens", ide_session_id, model, tokens)


def make_teach(deps: GraphDeps) -> Node:
    @node_timeout(150)
    async def teach(state: IdeTeacherState) -> IdeTeacherState:
        trigger: Trigger = state["trigger"]  # type: ignore[assignment]  # validated by the input
        if trigger == "run_ok":  # never a call: at most a compliment, filed by the route
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
