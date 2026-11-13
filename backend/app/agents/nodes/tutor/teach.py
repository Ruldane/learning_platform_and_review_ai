"""Le Tuteur enseigne (D102) : contexte de la séance, ouverture, une section à la fois (selon le
mode), l'exercice de la leçon, les trois questions finales, et le passage à la suite.

Aucun de ces nœuds n'écrit dans un port : rejoués après un arrêt, ils redemandent au modèle et
republient leurs messages sous le même id (le front remplace la bulle, D57). Le tableau n'a
aucune ligne `boards` (il n'est lié à aucun objectif) : seulement des `board.update`.
Journaux : identifiants et nombres seulement (SPEC 17.2)."""

import logging
import re
from dataclasses import asdict

from app.agents.nodes.memory_context import load_memory_context
from app.agents.nodes.mermaid_rules import (
    MAX_LABEL_CHARS,
    MAX_MERMAID_LINES,
    MAX_NODES,
    mermaid_problems,
    normalize_mermaid,
)
from app.agents.nodes.tutor.models import (
    AGENT,
    FinalQuestions,
    Node,
    TeachTurn,
    TutorReply,
    ask_tutor,
    context_of,
    lesson_prompt,
    notes_prompt,
    outcomes_prompt,
    say,
    section_text,
    tutor_prompt,
    whole_lesson,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import StudyContext
from app.core.errors import AppError

FINAL_COUNT = 3
MAX_MERMAID_CHARS = 2000
NO_MEMORY_CONTEXT = "Mémoire indisponible pour cette séance."
TEACH_REQUEST = "Prépare la section."
REPLY_REQUEST = "Réponds à January."
FINAL_REQUEST = "Écris les questions finales."
FINAL_INTRO = "Trois questions pour finir : elles reprennent toute la leçon."
_FENCE = re.compile(r"^```[a-z]*\s*\n|\n?```\s*$")
_MODES = {
    "socratic": "je te guide par des questions : c'est toi qui trouves.",
    "feynman": "tu m'expliques chaque section avec tes mots, je cherche les trous.",
    "direct": "je t'explique chaque section, puis je te pose une question.",
}

logger = logging.getLogger(__name__)


def first_position(context: StudyContext) -> tuple[str, int]:
    if context.sections:
        return "section", 0
    return ("exercise", 0) if context.exercise.strip() else ("final", 0)


def next_position(context: StudyContext, phase: str, index: int) -> tuple[str, int]:
    """Section suivante, puis l'exercice (s'il y en a un), puis les questions finales, puis la
    fin (`done`)."""
    if phase == "section" and index + 1 < len(context.sections):
        return "section", index + 1
    if phase == "section" and context.exercise.strip():
        return "exercise", 0
    if phase in ("section", "exercise"):
        return "final", 0
    return ("final", index + 1) if index + 1 < FINAL_COUNT else ("done", 0)


def route_position(state: StudySessionState) -> str:
    if state["phase"] == "done":
        return "ask_finish"
    if state["phase"] == "final" and not state.get("finals"):
        return "final_intro"
    return "teach"


def advance(state: StudySessionState) -> StudySessionState:
    """Question réglée : la suivante (pur, aucun appel)."""
    phase, index = next_position(context_of(state), state["phase"], state.get("index", 0))
    return {"phase": phase, "index": index, "hints": 0, "given_hints": [], "reply": None}


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: StudySessionState) -> StudySessionState:
        """La séance (port), puis le contexte mémoire proche du module (F24). Une mémoire
        indisponible n'arrête pas la séance : le Tuteur fait sans."""
        found = await deps.ports.study.context(deps.user_id, state["study_session_id"])
        try:
            memory = await load_memory_context(deps, objective=found.module_title, agent=AGENT)
            memory_text = memory.as_prompt()
        except AppError as exc:
            logger.warning(
                "Contexte mémoire indisponible : session %s (%s)", deps.session_id, exc.code
            )
            memory_text = NO_MEMORY_CONTEXT
        phase, index = first_position(found)
        return {
            "context": asdict(found),
            "memory": memory_text,
            "phase": phase,
            "index": index,
            "hints": 0,
            "given_hints": [],
            "outcomes": [],
            "board_step": 0,
            "last_input_seq": 0,
            "ended_early": False,
        }

    return context


def _opening(context: StudyContext) -> str:
    objectives = "\n".join(f"- {objective}" for objective in context.objectives)
    return (
        f"On travaille « {context.module_title} ».\n"
        + (f"Objectifs de la séance :\n{objectives}\n" if objectives else "")
        + f"Mode {_mode_name(context.mode)} : {_MODES[context.mode]}\n"
        "« Je bloque » te donne jusqu'à trois indices, « Passer » saute une question."
    )


def _mode_name(mode: str) -> str:
    return {"socratic": "socratique", "feynman": "Feynman", "direct": "direct"}[mode]


async def _reply(deps: GraphDeps, state: StudySessionState, notes: list[str], key: str) -> None:
    """Le Tuteur répond d'abord à ce que January a écrit (question d'ouverture, messages)."""
    prompt = tutor_prompt(
        state,
        "reply",
        memory=True,
        lesson=whole_lesson(context_of(state)),
        notes=notes_prompt(notes),
    )
    reply = await ask_tutor(
        deps, TutorReply, prompt, REPLY_REQUEST, step=f"reponse-{key}", intent="je te réponds"
    )
    say(state, reply.message, f"{AGENT}-reponse-{key}")


def make_open(deps: GraphDeps) -> Node:
    @node_timeout()
    async def open_session(state: StudySessionState) -> StudySessionState:
        """Objectif de la séance ; la question posée à l'ouverture reçoit sa réponse d'abord."""
        context = context_of(state)
        say(state, _opening(context), f"{AGENT}-objectif")
        if context.question and context.question.strip():
            await _reply(deps, state, [context.question], "ouverture")
        return {}

    return open_session


def draw_board(state: StudySessionState, code: str | None, title: str, *, session: str) -> int:
    """Publie le schéma s'il est valable (réémis, jamais le brut du modèle) ; trop long ou
    invalide, il est retiré, jamais un échec. Rend le dernier numéro d'étape du tableau."""
    step = state.get("board_step", 0)
    if not code or not code.strip():
        return step
    cleaned = _FENCE.sub("", code.strip()).strip()
    too_long = len(cleaned) > MAX_MERMAID_CHARS
    problems = ["trop long"] if too_long else mermaid_problems(cleaned)
    if problems:
        logger.info(
            "Schéma du Tuteur retiré : session %s, étape %d, %d problème(s), %d caractères",
            session,
            step + 1,
            len(problems),
            len(cleaned),
        )
        return step
    payload = {"mermaid": normalize_mermaid(cleaned), "step": step + 1, "title": title}
    emit("board.update", payload, agent=AGENT)
    return step + 1


async def _teach_section(
    deps: GraphDeps, state: StudySessionState, notes: list[str]
) -> StudySessionState:
    context, index = context_of(state), state["index"]
    section = context.sections[index]
    prompt = tutor_prompt(
        state,
        "teach",
        memory=True,
        section=lesson_prompt(section_text(section)),
        position=f"section {index + 1} sur {len(context.sections)}",
        notes=notes_prompt(notes),
        max_lines=MAX_MERMAID_LINES,
        max_nodes=MAX_NODES,
        max_chars=MAX_MERMAID_CHARS,
        max_label=MAX_LABEL_CHARS,
    )
    turn = await ask_tutor(
        deps,
        TeachTurn,
        prompt,
        TEACH_REQUEST,
        step=f"section-{index + 1}",
        intent="je prépare la section",
    )
    say(state, turn.message, f"{AGENT}-section-{index + 1}")
    step = draw_board(state, turn.mermaid, section.title, session=deps.session_id)
    return {"question": turn.question.strip(), "expected": turn.expected, "board_step": step}


def _pose_from_lesson(state: StudySessionState) -> StudySessionState:
    """Exercice : l'énoncé de la leçon, son corrigé pour réponse attendue (jamais écrit par le
    modèle). Question finale : celle de `final_intro`."""
    context, index = context_of(state), state["index"]
    if state["phase"] == "exercise":
        text = "Place à l'exercice de la leçon : prends ton temps, puis donne ta solution."
        say(state, text, f"{AGENT}-exercice")
        return {"question": context.exercise.strip(), "expected": context.solution.strip()}
    final = state["finals"][index]
    say(state, f"Question finale {index + 1} sur {FINAL_COUNT}.", f"{AGENT}-finale-{index + 1}")
    return {"question": final["question"], "expected": final["expected"]}


def make_teach(deps: GraphDeps) -> Node:
    @node_timeout()
    async def teach(state: StudySessionState) -> StudySessionState:
        """Les messages de January sont lus d'abord ; puis la question de la position."""
        last = state.get("last_input_seq", 0)
        inputs = await deps.user_inputs_since(last)
        notes = [text for said in inputs if (text := said.text.strip())]
        update: StudySessionState = {
            "last_input_seq": inputs[-1].seq if inputs else last,
            "hints": 0,
            "given_hints": [],
            "reply": None,
        }
        if state["phase"] == "section":
            return update | await _teach_section(deps, state, notes)
        if notes:
            await _reply(deps, state, notes, f"{state['phase']}-{state['index'] + 1}")
        return update | _pose_from_lesson(state)

    return teach


def make_final_intro(deps: GraphDeps) -> Node:
    @node_timeout()
    async def final_intro(state: StudySessionState) -> StudySessionState:
        """Les trois questions finales, écrites en une fois (rejoué : redemandées, rien d'écrit)."""
        prompt = tutor_prompt(
            state,
            "final",
            memory=True,
            lesson=whole_lesson(context_of(state)),
            outcomes=outcomes_prompt(state),
        )
        found = await ask_tutor(
            deps,
            FinalQuestions,
            prompt,
            FINAL_REQUEST,
            step="questions-finales",
            intent="je prépare les trois questions finales",
        )
        finals = [{"question": q.question.strip(), "expected": q.expected} for q in found.questions]
        say(state, FINAL_INTRO, f"{AGENT}-final")
        return {"finals": finals}

    return final_intro
