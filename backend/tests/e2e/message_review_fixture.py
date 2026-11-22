"""Données synthétiques pour la recette de Nod."""

from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep
from tests.support.telegram_review import MOMENT, add_card

router = APIRouter(prefix="/e2e/message-review")


@router.post("/card")
async def due_card(request: Request, current: CurrentUserDep) -> dict[str, str]:
    request.app.state.quiz.now = lambda: MOMENT
    return {"card_id": await add_card(request.app, current.id)}
