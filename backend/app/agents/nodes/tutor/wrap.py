"""Fin de séance (D102) : la question « Terminer la session » (point d'arrêt), le bilan du Tuteur
(aucune écriture), puis le rangement par le port et le message de fin.

La séance ne se termine que par cette question ou par « Terminer » (réponse `finish` à n'importe
quelle question, 5.6) : le temps vient du minuteur, la feature le compte. `wrap_up` est la seule
écriture du parcours, idempotente (session d'étude déjà `finished` : relue) ; le message de fin
vient après. Journaux : identifiants et nombres seulement (SPEC 17.2)."""

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from langgraph.types import interrupt

from app.agents.nodes.tutor.models import (
    AGENT,
    FINISH_SESSION,
    Node,
    SessionSummary,
    ask_tutor,
    context_of,
    outcomes_prompt,
    parse_tutor_answer,
    say,
    tutor_prompt,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import Outcome, StudyFinished, StudyOutcome, exercise_done
from app.core.errors import AppError

FINISH_QUESTION = "La séance est finie. Termine-la pour enregistrer ton temps et tes acquis."
FINISH_OPTION = {"value": "finish", "label": "Terminer la session"}
SUMMARY_REQUEST = "Rédige le bilan."
# Plus court que le plafond du nœud (120 s) : au-delà, le bilan chiffré, jamais `node_timeout`.
SUMMARY_TIMEOUT_S = 90.0
LEVEL_NAMES = {"declare": "Déclaré", "en_cours": "En cours", "valide": "Validé", "prouve": "Prouvé"}
SAVE_TIMEOUT_S = 300  # la feature range le temps, les tâches, les fiches, les acquis, le journal

logger = logging.getLogger(__name__)


def ask_finish(state: StudySessionState) -> StudySessionState:
    """Point d'arrêt de fin. Rien avant `interrupt()` ; toute autre réponse que `finish` repose
    la question."""
    value = interrupt(
        {"kind": FINISH_SESSION, "question": FINISH_QUESTION, "options": [FINISH_OPTION]}
    )
    answer = parse_tutor_answer(value)
    finished = answer is not None and answer.action == "finish"
    return {"reply": asdict(answer) if finished and answer is not None else None}


def route_finish(state: StudySessionState) -> str:
    return "summarize" if state.get("reply") else "ask_finish"


def outcomes_of(state: StudySessionState) -> list[Outcome]:
    return [Outcome(**o) for o in state.get("outcomes", [])]


def _fallback_summary(outcomes: list[Outcome]) -> str:
    good = sum(1 for o in outcomes if o.verdict == "correct")
    return f"Séance terminée : {good} réponse(s) juste(s) sur {len(outcomes)} question(s)."


def make_summarize(deps: GraphDeps) -> Node:
    @node_timeout()
    async def summarize(state: StudySessionState) -> StudySessionState:
        """Le bilan du Tuteur. Illisible après ses nouveaux essais, erreur du fournisseur ou délai
        dépassé : un bilan chiffré à la place (la séance n'échoue pas à la dernière marche ; revue
        finale de la phase 5, A-m1)."""
        outcomes = outcomes_of(state)
        prompt = tutor_prompt(
            state,
            "summary",
            outcomes=outcomes_prompt(state),
            ended_early=bool(state.get("ended_early")),
            exercise_done=exercise_done(outcomes),
        )
        try:
            async with asyncio.timeout(SUMMARY_TIMEOUT_S):
                found = await ask_tutor(
                    deps,
                    SessionSummary,
                    prompt,
                    SUMMARY_REQUEST,
                    step="bilan",
                    intent="je fais le bilan de la séance",
                )
        except (AppError, TimeoutError) as exc:
            code = exc.code if isinstance(exc, AppError) else "timeout"
            logger.warning(
                "Bilan indisponible (%s), bilan chiffré : session %s", code, deps.session_id
            )
            return {"session_summary": _fallback_summary(outcomes)}
        return {"session_summary": found.summary}

    return summarize


def _closing(summary: str, done: StudyFinished) -> str:
    tasks = ", ".join(f"« {title} »" for title in done.tasks_done) or "aucune"
    skills = ", ".join(f"{name} ({LEVEL_NAMES.get(level, level)})" for name, level in done.skills)
    lines = [
        summary,
        "",
        f"Temps enregistré : {done.minutes} min.",
        f"Tâches cochées : {tasks}.",
        f"Fiches créées depuis tes erreurs : {done.flashcards_created}.",
    ]
    if skills:
        lines.append(f"Acquis mis à jour : {skills}.")
    return "\n".join(lines)


def _finished_state(done: StudyFinished) -> dict[str, Any]:
    return {
        "minutes": done.minutes,
        "tasks_done": list(done.tasks_done),
        "flashcards_created": done.flashcards_created,
        "skills": [[name, level] for name, level in done.skills],
    }


def make_wrap_up(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def wrap_up(state: StudySessionState) -> StudySessionState:
        """La fin rangée par le port (idempotent), puis le message de fin."""
        outcomes = outcomes_of(state)
        result = StudyOutcome(
            outcomes=outcomes,
            exercise_done=exercise_done(outcomes),
            ended_early=bool(state.get("ended_early")),
            summary=state["session_summary"],
        )
        study_id = state["study_session_id"]
        done = await deps.ports.study.finish(deps.user_id, deps.session_id, study_id, result)
        logger.info(
            "Session d'étude rangée : session %s, étude %s, %d question(s), %d min, "
            "%d tâche(s), %d fiche(s)",
            deps.session_id,
            study_id,
            len(outcomes),
            done.minutes,
            len(done.tasks_done),
            done.flashcards_created,
        )
        say(state, _closing(state["session_summary"], done), f"{AGENT}-fin")
        title = context_of(state).module_title
        return {
            "finished": _finished_state(done),
            "summary": f"Session d'étude terminée : « {title} », {done.minutes} min.",
        }

    return wrap_up
