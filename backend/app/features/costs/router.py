"""Coûts de l'IA (SPEC 11.5, phase 9) : le rapport par jour, par fonction, par agent et par modèle,
et le journal des appels. Au nom de l'utilisatrice courante ; une 422 nomme les champs, sans
jamais recopier la valeur reçue."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, Db
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.features.costs.schemas import AgentCallPage, CostsReport

router = APIRouter(prefix="/costs", tags=["costs"], route_class=FieldPathsRoute)


@router.get("", response_model=CostsReport)
async def get_costs(
    current: CurrentUserDep, db: Db, days: Annotated[Literal[7, 30, 90], Query()] = 30
) -> CostsReport:
    """Les coûts des 7, 30 ou 90 derniers jours (jours du fuseau de l'utilisatrice, aujourd'hui
    compris), agrégés depuis les appels journalisés, aux prix de l'appel. Toute autre durée : 422
    (`details.fields` : `days`)."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)


@router.get(
    "/calls",
    response_model=AgentCallPage,
    responses={422: {"description": "`details.fields` : `before` (curseur illisible) ou `limit`"}},
)
async def get_calls(
    current: CurrentUserDep,
    db: Db,
    before: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    agent: Annotated[str | None, Query(max_length=64)] = None,
    graph: Annotated[str | None, Query(max_length=64)] = None,
) -> AgentCallPage:
    """Le journal des agents : les appels du plus récent au plus ancien, `limit` par page (50 par
    défaut). `before` est le curseur `next_before` de la page précédente ; `agent` et `graph`
    filtrent. Aucun contenu de prompt."""
    raise AppError("not_implemented", "Pas encore disponible.", 501)
