"""The Tutor (SPEC F14, 9.1, D102): runs a guided study session. It teaches the lesson section
by section according to the mode (Socratic, Feynman, direct), asks a question after each
section, then the lesson's exercise and three final questions; "I'm stuck" gives three graded
hints then the solution. Used by the `study_session` flow."""

from app.agents.nodes.tutor.answers import (
    ask,
    make_check,
    make_hint,
    reveal,
    route_answer,
    skip,
)
from app.agents.nodes.tutor.models import (
    AGENT,
    FINISH_SESSION,
    MAX_HINTS,
    TUTOR_QUESTION,
    AnswerCheck,
    FinalQuestion,
    FinalQuestions,
    HintTurn,
    SessionSummary,
    TeachTurn,
    TutorAnswer,
    TutorReply,
    parse_tutor_answer,
)
from app.agents.nodes.tutor.teach import (
    advance,
    make_context,
    make_final_intro,
    make_open,
    make_teach,
    route_position,
)
from app.agents.nodes.tutor.wrap import ask_finish, make_summarize, make_wrap_up, route_finish

__all__ = [
    "AGENT",
    "FINISH_SESSION",
    "MAX_HINTS",
    "TUTOR_QUESTION",
    "AnswerCheck",
    "FinalQuestion",
    "FinalQuestions",
    "HintTurn",
    "SessionSummary",
    "TeachTurn",
    "TutorAnswer",
    "TutorReply",
    "advance",
    "ask",
    "ask_finish",
    "make_check",
    "make_context",
    "make_final_intro",
    "make_hint",
    "make_open",
    "make_summarize",
    "make_teach",
    "make_wrap_up",
    "parse_tutor_answer",
    "reveal",
    "route_answer",
    "route_finish",
    "route_position",
    "skip",
]
