"""Un quiz écrit à la main est-il aux bornes de celui de l'Examinateur ? (phase 10, 10.W) : au moins
`MIN_QUESTIONS` questions, `MIN_TYPES` types différents et des énoncés de `MIN_PROMPT_CHARS`
caractères au moins, lues dans `app.agents.tools.quiz_port` (une seule source). Tant qu'il n'y est
pas, le quiz reste « en préparation » (`status.DRAFT_REASON`) et refuse toute tentative : une
réussite à 80 % fait passer les compétences du module à « validé »."""

from collections.abc import Sequence

from app.agents.tools.quiz_port import MIN_PROMPT_CHARS, MIN_QUESTIONS, MIN_TYPES
from app.db.models.study import QuizQuestion


def quiz_complete(questions: Sequence[QuizQuestion]) -> bool:
    return (
        len(questions) >= MIN_QUESTIONS
        and len({q.type for q in questions}) >= MIN_TYPES
        and all(len(q.prompt.strip()) >= MIN_PROMPT_CHARS for q in questions)
    )
