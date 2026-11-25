"""The Tutor teaches (D102): session context, opening, one section at a time (according to the
mode), the lesson's exercise, the three final questions, and the move to the next.

None of these nodes writes to a port: replayed after a stop, they ask the model again and
republish their messages under the same id (the front end replaces the bubble, D57). The board
has no `boards` row (it is tied to no goal): only `board.update`s.
Silent or too slow model (`fallback`, D115): section presented as written, final questions
taken from the lesson, January's message left unanswered; the session continues.
Logs: identifiers and numbers only (SPEC 17.2)."""

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
from app.agents.nodes.tutor.fallback import (
    FALLBACK_FINAL_INTRO,
    NO_REPLY,
    final_questions_from_lesson,
    teach_section_as_written,
    try_tutor,
)
from app.agents.nodes.tutor.models import (
    AGENT,
    FinalQuestions,
    Node,
    TeachTurn,
    TutorReply,
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
NO_MEMORY_CONTEXT = "Memory is unavailable for this session."
TEACH_REQUEST = "Prepare the section."
REPLY_REQUEST = "Reply to January."
FINAL_REQUEST = "Write the final questions."
FINAL_INTRO = "Three final questions cover the whole lesson."
_FENCE = re.compile(r"^```[a-z]*\s*\n|\n?```\s*$")
_MODES = {
    "socratic": "I’ll guide you with questions so you can find the answers.",
    "feynman": "Explain each section in your own words and I’ll look for gaps.",
    "direct": "I’ll explain each section and then ask you a question.",
}

logger = logging.getLogger(__name__)


def first_position(context: StudyContext) -> tuple[str, int]:
    if context.sections:
        return "section", 0
    return ("exercise", 0) if context.exercise.strip() else ("final", 0)


def next_position(context: StudyContext, phase: str, index: int) -> tuple[str, int]:
    """Next section, then the exercise (if there is one), then the final questions, then the
    end (`done`)."""
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
    """Question settled: the next one (pure, no call)."""
    phase, index = next_position(context_of(state), state["phase"], state.get("index", 0))
    return {"phase": phase, "index": index, "hints": 0, "given_hints": [], "reply": None}


def make_context(deps: GraphDeps) -> Node:
    @node_timeout()
    async def context(state: StudySessionState) -> StudySessionState:
        """The session (port), then the memory context close to the module (F24). Unavailable
        memory does not stop the session: the Tutor does without."""
        found = await deps.ports.study.context(deps.user_id, state["study_session_id"])
        try:
            memory = await load_memory_context(deps, objective=found.module_title, agent=AGENT)
            memory_text = memory.as_prompt()
        except AppError as exc:
            logger.warning("Memory context unavailable: session %s (%s)", deps.session_id, exc.code)
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
        f"We’ll study “{context.module_title}”.\n"
        + (f"Session objectives\n{objectives}\n" if objectives else "")
        + f"{_mode_name(context.mode)} mode. {_MODES[context.mode]}\n"
        "Choose ‘I’m stuck’ for up to three hints. Choose ‘Skip’ to move to the next question."
    )


def _mode_name(mode: str) -> str:
    return {"socratic": "Socratic", "feynman": "Feynman", "direct": "Direct"}[mode]


async def _reply(deps: GraphDeps, state: StudySessionState, notes: list[str], key: str) -> None:
    """The Tutor first answers what January wrote (opening question, messages)."""
    prompt = tutor_prompt(
        state,
        "reply",
        memory=True,
        lesson=whole_lesson(context_of(state)),
        notes=notes_prompt(notes),
    )
    reply = await try_tutor(
        deps, TutorReply, prompt, REPLY_REQUEST, step=f"reponse-{key}", intent="I’m replying"
    )
    say(state, reply.message if reply else NO_REPLY, f"{AGENT}-reponse-{key}")


def make_open(deps: GraphDeps) -> Node:
    @node_timeout()
    async def open_session(state: StudySessionState) -> StudySessionState:
        """Goal of the session; the question asked at the opening gets its answer first."""
        context = context_of(state)
        say(state, _opening(context), f"{AGENT}-objectif")
        if context.question and context.question.strip():
            await _reply(deps, state, [context.question], "ouverture")
        return {}

    return open_session


def draw_board(state: StudySessionState, code: str | None, title: str, *, session: str) -> int:
    """Publishes the diagram if it is valid (re-emitted, never the model's raw output); too long
    or invalid, it is removed, never a failure. Returns the board's last step number."""
    step = state.get("board_step", 0)
    if not code or not code.strip():
        return step
    cleaned = _FENCE.sub("", code.strip()).strip()
    too_long = len(cleaned) > MAX_MERMAID_CHARS
    problems = ["too long"] if too_long else mermaid_problems(cleaned)
    if problems:
        logger.info(
            "Tutor diagram removed: session %s, step %d, %d problem(s), %d characters",
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
        position=f"section {index + 1} of {len(context.sections)}",
        notes=notes_prompt(notes),
        max_lines=MAX_MERMAID_LINES,
        max_nodes=MAX_NODES,
        max_chars=MAX_MERMAID_CHARS,
        max_label=MAX_LABEL_CHARS,
    )
    turn = await try_tutor(
        deps,
        TeachTurn,
        prompt,
        TEACH_REQUEST,
        step=f"section-{index + 1}",
        intent="I’m preparing the section",
    )
    if turn is None:  # the section as written in the lesson, without a diagram (D115)
        message, question, expected = teach_section_as_written(state)
        say(state, message, f"{AGENT}-section-{index + 1}")
        return {"question": question, "expected": expected}
    say(state, turn.message, f"{AGENT}-section-{index + 1}")
    step = draw_board(state, turn.mermaid, section.title, session=deps.session_id)
    return {"question": turn.question.strip(), "expected": turn.expected, "board_step": step}


def _pose_from_lesson(state: StudySessionState) -> StudySessionState:
    """Exercise: the lesson's statement, its solution as the expected answer (never written by
    the model). Final question: the one from `final_intro`."""
    context, index = context_of(state), state["index"]
    if state["phase"] == "exercise":
        text = "Try the lesson exercise. Take your time and share your solution when ready."
        say(state, text, f"{AGENT}-exercice")
        return {"question": context.exercise.strip(), "expected": context.solution.strip()}
    final = state["finals"][index]
    say(state, f"Final question {index + 1} of {FINAL_COUNT}.", f"{AGENT}-finale-{index + 1}")
    return {"question": final["question"], "expected": final["expected"]}


def make_teach(deps: GraphDeps) -> Node:
    @node_timeout()
    async def teach(state: StudySessionState) -> StudySessionState:
        """January's messages are read first; then the question of the position."""
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
        """The three final questions, written at once (replayed: asked again, nothing written)."""
        prompt = tutor_prompt(
            state,
            "final",
            memory=True,
            lesson=whole_lesson(context_of(state)),
            outcomes=outcomes_prompt(state),
        )
        found = await try_tutor(
            deps,
            FinalQuestions,
            prompt,
            FINAL_REQUEST,
            step="questions-finales",
            intent="I’m preparing the three final questions",
        )
        if found is None:  # taken from the lesson's objectives and sections (D115)
            say(state, FALLBACK_FINAL_INTRO, f"{AGENT}-final")
            return {"finals": final_questions_from_lesson(context_of(state), FINAL_COUNT)}
        finals = [{"question": q.question.strip(), "expected": q.expected} for q in found.questions]
        say(state, FINAL_INTRO, f"{AGENT}-final")
        return {"finals": finals}

    return final_intro
