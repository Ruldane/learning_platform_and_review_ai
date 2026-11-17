"""API des quiz et des révisions (SPEC F9, 14.2 ; D101). Hors 14.2 : `POST /modules/{id}/quiz`
(quiz préparé à la demande), `GET /programs/{id}/quizzes` et `GET /quizzes/{id}/attempts/{id}`.
Tout est filtré par utilisateur : l'objet d'un autre donne 404."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from starlette.requests import HTTPConnection

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
from app.features.quiz.service.runtime import QuizRuntime

router = APIRouter(tags=["quiz"])


def get_quiz_runtime(conn: HTTPConnection) -> QuizRuntime:
    """Les quiz ouverts par le lifespan (`app.state.quiz`)."""
    runtime: QuizRuntime = conn.app.state.quiz
    return runtime


QuizDep = Annotated[QuizRuntime, Depends(get_quiz_runtime)]
_READY: dict[int | str, dict[str, Any]] = {
    200: {"model": QuizStarted, "description": "Quiz déjà prêt."}
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
    """Prépare le quiz du module (202) ; déjà prêt : 200 ; en préparation : même session ; en
    échec : relancé. Leçon pas prête : 409 `lesson_not_ready`."""
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
        409: {"description": "`quiz_exists`, `quiz_generating` ou `module_skipped`"},
    },
)
async def write_quiz(body: QuizWriteIn, current: CurrentUserDep, rt: QuizDep) -> QuizOut:
    """Écrit le quiz d'un module en direct (1 à 12 questions, sans fiches), sans agent ni appel au
    modèle ; la leçon du module n'a pas à être prête. Il reste « en préparation » (`generating`,
    sans session) tant qu'il n'a pas 8 questions, 3 types et des énoncés de 10 caractères : toute
    tentative donne alors 409 `quiz_incomplete`."""
    return await direct.create_quiz(rt, current.id, body)


@router.patch(
    "/quizzes/{quiz_id}",
    response_model=QuizOut,
    responses={404: {"description": "`quiz_not_found`"}, 409: {"description": "`quiz_not_ready`"}},
)
async def patch_quiz(
    quiz_id: str, body: QuizPatch, current: CurrentUserDep, rt: QuizDep
) -> QuizOut:
    """Change le titre d'un quiz prêt."""
    return await direct.patch_quiz(rt, current.id, quiz_id, body)


@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuizOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "`quiz_not_found`"},
        409: {"description": "`quiz_not_ready`, `quiz_has_attempts` ou `quiz_full`"},
    },
)
async def add_question(
    quiz_id: str, body: QuestionIn, current: CurrentUserDep, rt: QuizDep
) -> QuizOut:
    """Ajoute une question à un quiz prêt qui n'a pas de tentative, sans agent."""
    return await direct.add_question(rt, current.id, quiz_id, body)


@router.patch(
    "/quizzes/{quiz_id}/questions/{question_id}",
    response_model=QuizOut,
    responses={
        404: {"description": "`quiz_not_found` ou `question_not_found`"},
        409: {"description": "`quiz_not_ready` ou `quiz_has_attempts`"},
    },
)
async def patch_question(
    quiz_id: str, question_id: str, body: QuestionPatch, current: CurrentUserDep, rt: QuizDep
) -> QuizOut:
    """Retouche une question d'un quiz prêt qui n'a pas de tentative, sans agent."""
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
)
async def create_attempt(
    quiz_id: str, body: AttemptCreate, current: CurrentUserDep, rt: QuizDep
) -> AttemptStarted:
    """Envoie les réponses et lance la notation. 422 `invalid_answers` ; 409 `quiz_not_ready`,
    `attempt_in_progress` ou `retry_too_soon` (`details.retry_on`)."""
    return await attempts.create_attempt(rt, current.id, quiz_id, body)


@router.get("/quizzes/{quiz_id}/attempts/{attempt_id}", response_model=AttemptOut)
async def get_attempt(quiz_id: str, attempt_id: str, current: CurrentUserDep, db: Db) -> AttemptOut:
    return await attempts.get_attempt(db, current.id, quiz_id, attempt_id)


@router.get("/flashcards/due", response_model=DueQueue)
async def due_cards(current: CurrentUserDep, db: Db, rt: QuizDep) -> DueQueue:
    """La file du jour (30 fiches, 15 minutes, moins celles déjà revues aujourd'hui)."""
    return await cards.due_queue(rt, db, current.id)


@router.post("/flashcards/{card_id}/review", response_model=ReviewOut)
async def review_card(
    card_id: str, body: ReviewIn, current: CurrentUserDep, rt: QuizDep
) -> ReviewOut:
    """Avis sur une fiche due ; déjà revue : 409 `card_not_due` ; inconnue : 404."""
    return await cards.review_card(rt, current.id, card_id, body.result == "ok")
