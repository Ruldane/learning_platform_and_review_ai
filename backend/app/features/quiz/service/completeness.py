"""Is a hand-written quiz within the Examiner's bounds? (phase 10, 10.W): at least
`MIN_QUESTIONS` questions, `MIN_TYPES` different types and prompts of at least
`MIN_PROMPT_CHARS` characters, read from `app.agents.tools.quiz_port` (a single source). Until it
is, the quiz stays "being prepared" (`status.DRAFT_REASON`) and refuses any attempt: an 80%
pass moves the module's skills to "validated"."""

from collections.abc import Sequence

from app.agents.tools.quiz_port import MIN_PROMPT_CHARS, MIN_QUESTIONS, MIN_TYPES
from app.db.models.study import QuizQuestion


def quiz_complete(questions: Sequence[QuizQuestion]) -> bool:
    return (
        len(questions) >= MIN_QUESTIONS
        and len({q.type for q in questions}) >= MIN_TYPES
        and all(len(q.prompt.strip()) >= MIN_PROMPT_CHARS for q in questions)
    )
