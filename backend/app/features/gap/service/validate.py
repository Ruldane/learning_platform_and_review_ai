"""« Je les maîtrise déjà » depuis l'écart d'une offre (D220) : les compétences choisies (lignes
`to_add`) reçoivent un module « Valider mes acquis » dans le programme validé le plus récent, puis
l'Examinateur écrit son quiz ; réussi, il les passe à « validé ». Journaux : identifiants et
nombres seulement."""

import logging
from collections.abc import Sequence
from datetime import date

from app.features.gap.schemas import ValidateGapStarted
from app.features.gap.service.plan import chosen_skills, no_program
from app.features.gap.service.rows import gap_rows
from app.features.postings.service.queries import get_posting
from app.features.program.service.replan_gap import latest_validated
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.validation_module import add_validation_module
from app.features.quiz.service.quizzes import start_quiz
from app.features.quiz.service.runtime import QuizRuntime

logger = logging.getLogger(__name__)


async def validate_gap(
    program: ProgramRuntime,
    quiz: QuizRuntime,
    user_id: str,
    posting_id: str,
    skills: Sequence[str],
) -> ValidateGapStarted:
    """404 `posting_not_found`, 422 `gap_skill_unknown`, 409 `no_program`, 409 `week_full`."""
    async with program.session_factory() as db:
        posting = await get_posting(db, user_id, posting_id)
        names = chosen_skills(await gap_rows(db, user_id, posting), skills)
        program_id = await latest_validated(db, user_id)
    if program_id is None:
        raise no_program()
    module_id = await add_validation_module(program, user_id, program_id, names, date.today())
    started = await start_quiz(quiz, user_id, module_id)
    logger.info(
        "Validation des acquis : offre %s, module %s, %d compétence(s), quiz %s",
        posting_id,
        module_id,
        len(names),
        started.quiz_id,
    )
    return ValidateGapStarted(
        module_id=module_id, quiz_id=started.quiz_id, session_id=started.session_id
    )
