"""The Tutor without a model answer (check 5.18, D115): a slow, hung or unreadable call or a
transient provider failure never makes the session fail.

Each Tutor call has its deadline (`TUTOR_CALL_TIMEOUT_S`), shorter than the node cap (120 s):
the margin lets the fallback be written. A Tutor node makes a single model call; beyond the
deadline, it does not retry, it falls back (replayed, it asks once again, as before). The
fallbacks come from the lesson (section as written, questions taken from the objectives and
sections), never an invented text. A refused key, an exhausted credit or the token cap remain
failures: the session must not continue without saying so.
Logs: identifiers and error code only (SPEC 17.2)."""

import asyncio
import logging

from pydantic import BaseModel

from app.agents.nodes.tutor.models import ask_tutor, context_of
from app.agents.runtime.deps import GraphDeps
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import LessonSection, StudyContext
from app.core.errors import AppError

# Shorter than a node's cap (`NODE_TIMEOUT_S`, 120 s): the fallback only does two `emit`s
# (a few milliseconds), 15 s of margin are enough for the reads done before the call.
TUTOR_CALL_TIMEOUT_S = 105.0
# Slowness, transient failure, empty or unreadable reply: we fall back. The rest fails,
# including `llm_rate_limited` (429 still there after the retries: often a Z.ai quota exhausted
# for the period, which the session must say instead of continuing without grading; D115 no. 17).
RECOVERABLE_CODES = frozenset(
    {"llm_timeout", "llm_unavailable", "llm_empty_reply", "structured_output_invalid"}
)
UNCHECKED = "I couldn’t check this answer. Let’s continue."
NO_REPLY = "I couldn’t answer your message. Let’s continue."
FALLBACK_FINAL_INTRO = "Three final questions based on the lesson objectives and sections."
NO_SOLUTION = "There’s no prepared solution for this question. Review the lesson to try again."
NO_EXPECTED = "(none)"
MAX_QUESTION_CHARS = 500
MAX_EXPECTED_CHARS = 800

logger = logging.getLogger(__name__)


async def try_tutor[T: BaseModel](
    deps: GraphDeps, schema: type[T], prompt: str, request: str, *, step: str, intent: str
) -> T | None:
    """`ask_tutor` under the Tutor's deadline; `None` if the model did not answer in time or
    readably (the node falls back). Other errors bubble up."""
    try:
        async with asyncio.timeout(TUTOR_CALL_TIMEOUT_S):
            return await ask_tutor(deps, schema, prompt, request, step=step, intent=intent)
    except (AppError, TimeoutError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        if code != "timeout" and code not in RECOVERABLE_CODES:
            raise
        logger.warning(
            "Tutor without a model answer (%s), fallback: session %s, step %s",
            code,
            deps.session_id,
            step,
        )
        return None


def excerpt(text: str, limit: int = MAX_EXPECTED_CHARS) -> str:
    """`text` cut at `limit` characters, on a space, with "..." if it is cut."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip() + "…"


def hint_unavailable(level: int, max_hints: int) -> str:
    then = (
        "Choose ‘I’m stuck’ for the next hint, or answer the question."
        if level < max_hints
        else "You can show the solution or answer the question."
    )
    return f"I couldn’t prepare hint {level} of {max_hints}. {then}"


def section_question(section: LessonSection) -> tuple[str, str]:
    """Question and expected answer of a section, taken from the lesson."""
    question = f"What did you learn from “{section.title}”? Explain it in your own words."
    return excerpt(question, MAX_QUESTION_CHARS), excerpt(section.markdown) or section.title


def teach_section_as_written(state: StudySessionState) -> tuple[str, str, str]:
    """Message, question and expected answer of the current section, without the model."""
    section = context_of(state).sections[state["index"]]
    message = (
        "I couldn’t prepare this section. You can read it as written in the lesson.\n\n"
        f"## {section.title}\n\n{section.markdown.strip()}"
    )
    question, expected = section_question(section)
    return message, question, expected


def final_questions_from_lesson(context: StudyContext, count: int) -> list[dict[str, str]]:
    """`count` final questions without the model: the objectives, then the sections, then
    general questions about the module (always `count`, never a duplicate). Only the section
    questions have an expected answer (the start of their section): the others have none
    (`""`), judged against the whole lesson, with no card or foreign "solution" (D115 no. 17)."""
    title = context.module_title
    candidates = [
        (f"How would you explain “{objective.strip()}” in your own words?", "")
        for objective in context.objectives
    ]
    candidates += [section_question(s) for s in context.sections]
    candidates += [
        (f"What did you learn from “{title}”?", ""),
        (f"What idea from “{title}” will you apply, and how?", ""),
        (f"What mistake should you avoid when applying “{title}”, and why?", ""),
    ]
    finals: list[dict[str, str]] = []
    for question, expected in candidates:
        question = excerpt(question, MAX_QUESTION_CHARS)
        if question and all(f["question"] != question for f in finals):
            finals.append({"question": question, "expected": expected})
    return finals[:count]
