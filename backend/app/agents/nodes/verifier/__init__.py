"""Le Vérificateur (SPEC 3.5, 9.1) : contrôles déterministes d'une leçon, puis des faits."""

from app.agents.nodes.verifier.checks import (
    MAX_WORDS,
    MIN_WORDS,
    SECTIONS,
    LessonCheck,
    check_lesson,
)
from app.agents.nodes.verifier.overlap import MAX_QUOTE_WORDS
from app.agents.nodes.verifier.prune import IN_SCOPE, Pruned, in_scope, prune
from app.agents.nodes.verifier.verify import MAX_REVISIONS, FactReport, make_verify, route_verify

__all__ = [
    "IN_SCOPE",
    "MAX_QUOTE_WORDS",
    "MAX_REVISIONS",
    "MAX_WORDS",
    "MIN_WORDS",
    "SECTIONS",
    "FactReport",
    "LessonCheck",
    "Pruned",
    "check_lesson",
    "in_scope",
    "make_verify",
    "prune",
    "route_verify",
]
