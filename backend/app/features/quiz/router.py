"""Quiz and review API (SPEC F9, 14.2; D101). Outside 14.2: `POST /modules/{id}/quiz`
(quiz prepared on demand), `GET /programs/{id}/quizzes` and `GET /quizzes/{id}/attempts/{id}`.
Everything is filtered by user: another user's object gives 404."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from starlette.requests import HTTPConnection

from app.core.caller import ConfirmedGesture
from app.core.deps import CurrentUserDep, Db
from app.features.quiz.schemas import (
    AttemptCreate,
    AttemptOut,
    AttemptStarted,
    DueQueue,
    QuestionIn,
    QuestionPatch,
    QuizOut,
    QuizPatch,
    QuizStarted,
    QuizSummaryOut,
    QuizWriteIn,
    ReviewIn,
    ReviewOut,
)
from app.features.quiz.service import attempts, cards, direct, quizzes
from app.features.quiz.service.offline import review_offline
from app.features.quiz.service.runtime import QuizRuntime

router = APIRouter(tags=["quiz"])


def get_quiz_runtime(conn: HTTPConnection) -> QuizRuntime:
    """The quizzes opened by the lifespan (`app.state.quiz`)."""
    runtime: QuizRuntime = conn.app.state.quiz
    return runtime


QuizDep = Annotated[QuizRuntime, Depends(get_quiz_runtime)]
_READY: dict[int | str, dict[str, Any]] = {
    200: {"model": QuizStarted, "description": "Quiz already ready."}
}


@router.post(
    "/modules/{module_id}/quiz",
    response_model=QuizStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_READY,
)
async def start_quiz(
    module_id: str, current: CurrentUserDep, rt: QuizDep, response: Response
) -> QuizStarted:
    """Prepares the module quiz (202); already ready: 200; being prepared: same session;
    failed: relaunched. Lesson not ready: 409 `lesson_not_ready`."""
    started = await quizzes.start_quiz(rt, current.id, module_id)
    if started.status == "ready":
        response.status_code = status.HTTP_200_OK
    return started


@router.post(
    "/quizzes",
    response_model=QuizOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "`module_not_found`"},
        409: {"description": "`quiz_exists`, `quiz_generating` or `module_skipped`"},
    },
)
async def write_quiz(body: QuizWriteIn, current: CurrentUserDep, rt: QuizDep) -> QuizOut:
    """Writes a module quiz directly (1 to 12 questions, no cards), with no agent and no model
    call; the module lesson need not be ready. It stays "being prepared" (`generating`, no
    session) until it has 8 questions, 3 types and prompts of 10 characters: until then any
    attempt gives 409 `quiz_incomplete`."""
    return await direct.create_quiz(rt, current.id, body)


@router.patch(
    "/quizzes/{quiz_id}",
    response_model=QuizOut,
    responses={404: {"description": "`quiz_not_found`"}, 409: {"description": "`quiz_not_ready`"}},
)
async def patch_quiz(
    quiz_id: str, body: QuizPatch, current: CurrentUserDep, rt: QuizDep
) -> QuizOut:
    """Changes the title of a ready quiz."""
    return await direct.patch_quiz(rt, current.id, quiz_id, body)


@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuizOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "`quiz_not_found`"},
        409: {"description": "`quiz_not_ready`, `quiz_has_attempts` or `quiz_full`"},
    },
)
async def add_question(
    quiz_id: str, body: QuestionIn, current: CurrentUserDep, rt: QuizDep
) -> QuizOut:
    """Adds a question to a ready quiz with no attempt, without an agent."""
    return await direct.add_question(rt, current.id, quiz_id, body)


@router.patch(
    "/quizzes/{quiz_id}/questions/{question_id}",
    response_model=QuizOut,
    responses={
        404: {"description": "`quiz_not_found` or `question_not_found`"},
        409: {"description": "`quiz_not_ready` or `quiz_has_attempts`"},
    },
)
async def patch_question(
    quiz_id: str, question_id: str, body: QuestionPatch, current: CurrentUserDep, rt: QuizDep
) -> QuizOut:
    """Edits a question of a ready quiz with no attempt, without an agent."""
    return await direct.patch_question(rt, current.id, quiz_id, question_id, body)


@router.get("/programs/{program_id}/quizzes", response_model=list[QuizSummaryOut])
async def list_quizzes(program_id: str, current: CurrentUserDep, db: Db) -> list[QuizSummaryOut]:
    return await quizzes.list_quizzes(db, current.id, program_id)


@router.get("/quizzes/{quiz_id}", response_model=QuizOut)
async def get_quiz(quiz_id: str, current: CurrentUserDep, db: Db) -> QuizOut:
    return await quizzes.get_quiz(db, current.id, quiz_id)


@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=AttemptStarted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[ConfirmedGesture],
)
async def create_attempt(
    quiz_id: str, body: AttemptCreate, current: CurrentUserDep, rt: QuizDep
) -> AttemptStarted:
    """Submits the answers and starts grading. 422 `invalid_answers`; 409 `quiz_not_ready`,
    `attempt_in_progress` or `retry_too_soon` (`details.retry_on`)."""
    return await attempts.create_attempt(rt, current.id, quiz_id, body)


@router.get("/quizzes/{quiz_id}/attempts/{attempt_id}", response_model=AttemptOut)
async def get_attempt(quiz_id: str, attempt_id: str, current: CurrentUserDep, db: Db) -> AttemptOut:
    return await attempts.get_attempt(db, current.id, quiz_id, attempt_id)


@router.get("/flashcards/due", response_model=DueQueue)
async def due_cards(current: CurrentUserDep, db: Db, rt: QuizDep) -> DueQueue:
    """Today's queue (30 cards, 15 minutes, minus those already reviewed today)."""
    return await cards.due_queue(rt, db, current.id)


@router.post(
    "/flashcards/{card_id}/review", response_model=ReviewOut, dependencies=[ConfirmedGesture]
)
async def review_card(
    card_id: str, body: ReviewIn, current: CurrentUserDep, rt: QuizDep
) -> ReviewOut:
    """Review of a due card; already reviewed: 409 `card_not_due`; unknown: 404."""
    if body.receipt is not None:
        return await review_offline(rt, current.id, card_id, body.result == "ok", body.receipt)
    return await cards.review_card(rt, current.id, card_id, body.result == "ok")
