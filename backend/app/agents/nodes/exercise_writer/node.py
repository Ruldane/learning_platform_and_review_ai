"""Le rédacteur d'exercices (10.A3) : un exercice avec ses tests et une solution de référence, que
le bac à sable fait passer avant que l'exercice soit rangé. Une solution qui échoue à ses propres
tests est redemandée une fois (avec la fin de la sortie des tests), puis le parcours échoue avec un
message lisible (`exercise_unverified`) : un exercice jamais vérifié n'est jamais rangé. Les tests
de l'exercice s'imposent à la solution (le port les remet par-dessus). La solution n'est jamais
rangée. Journaux : identifiants, nombres et codes."""

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
ASK = "Écris l'exercice."
ATTEMPTS = 2  # la première écriture, puis une seule redemande
LEVELS = {"beginner": "débutante", "intermediate": "intermédiaire", "advanced": "avancée"}
FEEDBACK_MAX = 1_500

logger = logging.getLogger(__name__)


def summary_of(title: str) -> str:
    return f"Exercice prêt : {title}"


def unverified() -> AppError:
    return AppError(
        "exercise_unverified",
        "The generated exercise failed its sandbox tests. Generate it again.",
        502,
    )


def _prompt(state: IdeExerciseState, previous: str | None) -> list[BaseMessage]:
    text = render_prompt(
        AGENT,
        topic=untrusted(state["topic"], "sujet demandé"),
        level=LEVELS.get(state.get("level", "beginner"), LEVELS["beginner"]),
        previous=untrusted(previous, "sortie des tests") if previous else "",
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
                "Exercice : session %s, essai %d/%d, tests %s (%s)",
                deps.session_id,
                attempt,
                ATTEMPTS,
                "réussis" if verdict.passed else "échoués",
                verdict.status,
            )
            if verdict.passed:
                await ports.save_exercise(deps.user_id, deps.session_id, draft, state["topic"])
                return {"summary": summary_of(draft.title)}
            previous = verdict.output[-FEEDBACK_MAX:] or f"({verdict.status})"
        raise unverified()

    return write
