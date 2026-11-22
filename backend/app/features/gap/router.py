"""API de l'écart (SPEC F8, D122, D123) : le tableau d'une offre, recalculé à chaque lecture, les
compétences qui manquent le plus souvent dans les offres de January et « Ajouter au planning »
(une replanification au déclencheur `gap`, validée par January)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.gap.schemas import (
    GapOut,
    GapSkillsIn,
    PlanGapIn,
    PlanGapStarted,
    TopMissingOut,
    ValidateGapStarted,
)
from app.features.gap.service.plan import plan_gap
from app.features.gap.service.top import top_missing_skills
from app.features.gap.service.validate import validate_gap
from app.features.gap.service.view import posting_gap
from app.features.program.service.runtime import ProgramRuntime
from app.features.quiz.service.runtime import QuizRuntime
from app.features.replan.service.runtime import ReplanRuntime

router = APIRouter(tags=["gap"])


def get_replan_runtime(conn: HTTPConnection) -> ReplanRuntime:
    """La replanification ouverte par le lifespan (`app.state.replan`)."""
    runtime: ReplanRuntime = conn.app.state.replan
    return runtime


ReplanDep = Annotated[ReplanRuntime, Depends(get_replan_runtime)]


@router.get("/postings/{posting_id}/gap", response_model=GapOut)
async def get_gap(posting_id: str, current: CurrentUserDep, db: Db) -> GapOut:
    """`pending` tant que l'analyse tourne ; offre d'une autre : 404 `posting_not_found`."""
    return await posting_gap(db, current.id, posting_id)


@router.post(
    "/postings/{posting_id}/gap/plan",
    response_model=PlanGapStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_gap_plan(
    posting_id: str, body: PlanGapIn, current: CurrentUserDep, rt: ReplanDep
) -> PlanGapStarted:
    """Propose les ajouts au programme validé choisi, par défaut le plus récent.

    422 `gap_skill_unknown` si une ligne ne peut pas être ajoutée. 404 `program_not_found`,
    409 `program_not_validated`, `no_program` ou `replan_open` suivant le programme.
    """
    session_id = await plan_gap(rt, current.id, posting_id, body.skills, program_id=body.program_id)
    return PlanGapStarted(session_id=session_id)


def get_program_runtime(conn: HTTPConnection) -> ProgramRuntime:
    runtime: ProgramRuntime = conn.app.state.program
    return runtime


def get_quiz_runtime(conn: HTTPConnection) -> QuizRuntime:
    runtime: QuizRuntime = conn.app.state.quiz
    return runtime


@router.post(
    "/postings/{posting_id}/gap/validate",
    response_model=ValidateGapStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_gap_validate(
    posting_id: str,
    body: GapSkillsIn,
    current: CurrentUserDep,
    program: Annotated[ProgramRuntime, Depends(get_program_runtime)],
    quiz: Annotated[QuizRuntime, Depends(get_quiz_runtime)],
) -> ValidateGapStarted:
    """« Je les maîtrise déjà » (D220) : un module « Valider mes acquis » avec ces compétences dans
    le programme validé le plus récent, et son quiz écrit par l'Examinateur ; réussi, il les passe
    à « validé ». 422 `gap_skill_unknown`, 409 `no_program`, 409 `week_full`."""
    return await validate_gap(program, quiz, current.id, posting_id, body.skills)


@router.get("/gap/top-missing", response_model=list[TopMissingOut])
async def get_top_missing(current: CurrentUserDep, db: Db) -> list[TopMissingOut]:
    """Les 10 compétences absentes demandées par le plus d'offres."""
    found = await top_missing_skills(db, current.id)
    return [
        TopMissingOut(skill=m.skill, postings=m.postings, required_in=m.required_in) for m in found
    ]
