"""The exercise writer (10.A3): an exercise with its tests and a reference solution, which the
sandbox runs before the exercise is filed. A solution that fails its own tests is requested again
once (with the end of the test output), then the flow fails with a readable message
(`exercise_unverified`): a never-verified exercise is never filed. The exercise's tests are
imposed on the solution (the port puts them back on top). The solution is never filed. Logs:
identifiers, numbers and codes."""

import logging

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.ide_exercise import IdeExerciseState, Node
from app.agents.tools.ide_schema import ExerciseDraft
from app.core.errors import AppError

__all__ = ["AGENT", "ATTEMPTS", "make_write", "summary_of"]

AGENT = "exercise_writer"
ASK = "Write the exercise."
ATTEMPTS = 2  # the first writing, then a single re-request
LEVELS = {"beginner": "beginner", "intermediate": "intermediate", "advanced": "advanced"}
FEEDBACK_MAX = 1_500

logger = logging.getLogger(__name__)


def summary_of(title: str) -> str:
    return f"Exercise ready: {title}"


def unverified() -> AppError:
    return AppError(
        "exercise_unverified",
        "The generated exercise failed its sandbox tests. Generate it again.",
        502,
    )


def _prompt(state: IdeExerciseState, previous: str | None) -> list[BaseMessage]:
    text = render_prompt(
        AGENT,
        topic=untrusted(state["topic"], "requested topic"),
        level=LEVELS.get(state.get("level", "beginner"), LEVELS["beginner"]),
        previous=untrusted(previous, "test output") if previous else "",
    )
    return [SystemMessage(text), HumanMessage(ASK)]


def make_write(deps: GraphDeps) -> Node:
    @node_timeout(300)
    async def write(state: IdeExerciseState) -> IdeExerciseState:
        ports = deps.ports.ide
        tier = get_agent(AGENT).tier
        previous: str | None = None
        for attempt in range(1, ATTEMPTS + 1):
            model = await deps.models.get_chat_model(deps.user_id, tier, agent=AGENT)
            draft = await structured_call(
                model,
                ExerciseDraft,
                _prompt(state, previous),
                agent=AGENT,
                step="exercice",
                intent="writing the exercise and its tests",
            )
            verdict = await ports.verify(deps.user_id, draft)
            logger.info(
                "Exercise: session %s, attempt %d/%d, tests %s (%s)",
                deps.session_id,
                attempt,
                ATTEMPTS,
                "passed" if verdict.passed else "failed",
                verdict.status,
            )
            if verdict.passed:
                await ports.save_exercise(deps.user_id, deps.session_id, draft, state["topic"])
                return {"summary": summary_of(draft.title)}
            previous = verdict.output[-FEEDBACK_MAX:] or f"({verdict.status})"
        raise unverified()

    return write
