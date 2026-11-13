"""Les réponses de January (D102) : la question posée (point d'arrêt), puis le verdict, un indice,
la solution ou le saut.

`ask` ne fait qu'`interrupt()` puis lit la réponse (pur) : rien avant l'arrêt (SPEC 9.4). Une
réponse illisible repose la même question. « Je bloque » et « Passer » sont des options de la
question ; le libellé de « Je bloque » porte le compte des indices (« Je bloque (1/3) »), puis
devient « Voir la solution » : le front ne compte rien (F15). La réponse de January est encadrée
comme non fiable (SPEC 17.4) : une consigne qu'elle contient ne change pas le verdict.
Modèle muet ou trop lent (`fallback`, D115) : réponse non corrigée (`skipped`), indice compté
sans texte ; la séance continue."""

import logging
from dataclasses import asdict
from typing import Any

from langgraph.types import interrupt

from app.agents.nodes.tutor.fallback import UNCHECKED, hint_unavailable, try_tutor
from app.agents.nodes.tutor.models import (
    ANSWER_LABEL,
    MAX_ANSWER_CHARS,
    MAX_HINTS,
    TUTOR_QUESTION,
    AnswerCheck,
    HintTurn,
    Node,
    context_of,
    lesson_prompt,
    outcome_record,
    parse_tutor_answer,
    say,
    section_text,
    tutor_prompt,
    whole_lesson,
)
from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.study_session import StudySessionState

CHECK_REQUEST = "Évalue la réponse."
HINT_REQUEST = "Donne l'indice."
REVEAL_LABEL = "Voir la solution"
SKIP_OPTION = {"value": "skip", "label": "Passer"}
ANSWER_FIELD = {"id": "answer", "label": "Ta réponse", "max_length": MAX_ANSWER_CHARS}

logger = logging.getLogger(__name__)


def stuck_label(hints: int) -> str:
    """« Je bloque (n/3) » pour l'indice n à venir ; « Voir la solution » une fois épuisés."""
    return REVEAL_LABEL if hints >= MAX_HINTS else f"Je bloque ({hints + 1}/{MAX_HINTS})"


def question_payload(state: StudySessionState) -> dict[str, Any]:
    stuck = {"value": "stuck", "label": stuck_label(state.get("hints", 0))}
    return {
        "kind": TUTOR_QUESTION,
        "question": state["question"],
        "options": [stuck, SKIP_OPTION],
        "fields": [ANSWER_FIELD],
    }


def ask(state: StudySessionState) -> StudySessionState:
    """Point d'arrêt : la question en cours. Rien avant `interrupt()`."""
    answer = parse_tutor_answer(interrupt(question_payload(state)))
    if answer is None:
        return {"reply": None}
    if answer.action == "finish":
        return {"reply": asdict(answer), "ended_early": True}
    return {"reply": asdict(answer)}


def route_answer(state: StudySessionState) -> str:
    reply = state.get("reply")
    if reply is None:
        return "ask"
    action = reply["action"]
    if action == "stuck":
        return "hint" if state.get("hints", 0) < MAX_HINTS else "reveal"
    return {"answer": "check", "skip": "skip", "finish": "summarize"}[action]


def _key(state: StudySessionState) -> str:
    return f"{state['phase']}-{state.get('index', 0) + 1}"


def _reference(state: StudySessionState) -> str:
    """Ce qui sert à juger : la section, l'énoncé de l'exercice, ou toute la leçon (finale)."""
    context = context_of(state)
    if state["phase"] == "section":
        return lesson_prompt(section_text(context.sections[state["index"]]))
    if state["phase"] == "exercise":
        return lesson_prompt(f"## Exercice\n\n{context.exercise}")
    return whole_lesson(context)


def _item(state: StudySessionState) -> str:
    """Question et réponse attendue : écrites par le Tuteur ou tirées de la leçon (non fiable)."""
    text = f"Question : {state['question']}\nRéponse attendue : {state['expected']}"
    return untrusted(text, "question")


def make_check(deps: GraphDeps) -> Node:
    @node_timeout()
    async def check(state: StudySessionState) -> StudySessionState:
        reply = state["reply"]
        assert reply is not None  # garanti par `route_answer`
        prompt = tutor_prompt(
            state,
            "check",
            reference=_reference(state),
            item=_item(state),
            answer=untrusted(reply["text"], ANSWER_LABEL),
        )
        found = await try_tutor(
            deps,
            AnswerCheck,
            prompt,
            CHECK_REQUEST,
            step=f"verdict-{_key(state)}",
            intent="je lis ta réponse",
        )
        # Sans verdict du modèle : `skipped`, ni fiche ni pratique cochée (F13, D115).
        verdict = found.verdict if found else "skipped"
        say(state, found.feedback if found else UNCHECKED, f"tutor-retour-{_key(state)}")
        logger.info(
            "Réponse jugée : session %s, %s, verdict %s, %d indice(s)",
            deps.session_id,
            _key(state),
            verdict,
            state.get("hints", 0),
        )
        return {"outcomes": outcome_record(state, verdict)}

    return check


def _previous(hints: list[str]) -> str:
    if not hints:
        return "Aucun."
    return untrusted("\n".join(f"{n}. {h}" for n, h in enumerate(hints, start=1)), "indices")


def make_hint(deps: GraphDeps) -> Node:
    @node_timeout()
    async def hint(state: StudySessionState) -> StudySessionState:
        """Indice gradué : 1 une piste, 2 la méthode, 3 presque la réponse ; puis la question
        est reposée, avec le compte à jour."""
        level = state.get("hints", 0) + 1
        given = state.get("given_hints", [])
        prompt = tutor_prompt(
            state,
            "hint",
            level=level,
            reference=_reference(state),
            item=_item(state),
            previous=_previous(given),
        )
        found = await try_tutor(
            deps,
            HintTurn,
            prompt,
            HINT_REQUEST,
            step=f"indice-{_key(state)}-{level}",
            intent="je prépare un indice",
        )
        message_id = f"tutor-indice-{_key(state)}-{level}"
        if found is None:  # l'indice compte : la solution reste à trois clics, sans le modèle
            say(state, hint_unavailable(level, MAX_HINTS), message_id)
            return {"hints": level, "given_hints": given}
        say(state, f"Indice {level} sur {MAX_HINTS} : {found.hint}", message_id)
        return {"hints": level, "given_hints": [*given, found.hint]}

    return hint


def reveal(state: StudySessionState) -> StudySessionState:
    """Après trois indices : la solution (la réponse attendue), et la question est réglée."""
    say(state, f"Voici la solution :\n\n{state['expected']}", f"tutor-solution-{_key(state)}")
    return {"outcomes": outcome_record(state, "revealed")}


def skip(state: StudySessionState) -> StudySessionState:
    return {"outcomes": outcome_record(state, "skipped")}
