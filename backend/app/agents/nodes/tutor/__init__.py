"""Le Tuteur (SPEC F14, 9.1, D102) : mène une séance d'étude guidée. Il enseigne la leçon section
par section selon le mode (socratique, Feynman, direct), pose une question après chaque section,
puis l'exercice de la leçon et trois questions finales ; « Je bloque » donne trois indices
gradués puis la solution. Utilisé par le parcours `study_session`."""

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
