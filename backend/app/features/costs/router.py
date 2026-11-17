"""Coûts de l'IA (SPEC 11.5, phase 9) : le rapport par jour, par fonction, par agent et par modèle,
et le journal des appels. Au nom de l'utilisatrice courante ; une 422 nomme les champs, sans
jamais recopier la valeur reçue."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BeforeValidator

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.costs.schemas import AgentCallPage, CostsReport
from app.features.costs.service import costs_report, list_calls

router = APIRouter(prefix="/costs", tags=["costs"], route_class=FieldPathsRoute)


def _days_from_query(value: object) -> object:
    """Un paramètre de requête arrive en texte : pydantic ne lit pas « 7 » comme l'entier 7 pour
    un `Literal`. Seuls les chiffres ASCII sont convertis ; le reste reste tel quel, donc refusé."""
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    return value


Days = Annotated[Literal[7, 30, 90], BeforeValidator(_days_from_query)]


@router.get(
    "",
    response_model=CostsReport,
    responses={422: {"description": "`details.fields` : `days` (ni 7, ni 30, ni 90)"}},
)
async def get_costs(
    current: CurrentUserDep, db: Db, days: Annotated[Days, Query()] = 30
) -> CostsReport:
    """Les coûts des 7, 30 ou 90 derniers jours (jours du fuseau de l'utilisatrice, aujourd'hui
    compris), agrégés depuis les appels journalisés, aux prix de l'appel. Toute autre durée : 422
    (`details.fields` : `days`)."""
    return await costs_report(db, current.id, days)


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
    return await list_calls(db, current.id, before=before, limit=limit, agent=agent, graph=graph)
