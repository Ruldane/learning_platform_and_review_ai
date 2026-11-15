"""API du comité de recrutement simulé (SPEC F19, D147) : lancement du parcours `hiring_committee`
sur une version de CV prête, liste et détail (votes, verdict, objections, changements, avant et
après). Toutes au nom de l'utilisatrice courante ; une 422 nomme les champs, sans jamais citer
l'entrée. L'écran dit qu'il s'agit d'une simulation, jamais d'une prédiction."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.applications.router import ApplicationsDep, Id
from app.features.applications.schemas_committee import (
    CommitteeIn,
    CommitteeRunOut,
    CommitteeStartOut,
)
from app.features.applications.service.committee import get_run, list_runs, start_committee

router = APIRouter(prefix="/committee", tags=["committee"], route_class=FieldPathsRoute)

_START: dict[int | str, dict[str, Any]] = {
    404: {"description": "`version_not_found`, `posting_not_found`"},
    409: {
        "description": (
            "`version_not_ready` (le PDF de la version n'est pas rendu), "
            "`committee_in_progress` (`details.run_id` : l'exécution ouverte de l'offre), "
            "`profile_required` (aucun profil maître validé)"
        )
    },
    503: {"description": "`engine_unavailable`"},
}


@router.post("", response_model=CommitteeStartOut, status_code=202, responses=_START)
async def post_committee(
    body: CommitteeIn, current: CurrentUserDep, rt: ApplicationsDep
) -> CommitteeStartOut:
    """Réunit le comité sur la version de CV : impressions, deux tours de débat, votes et
    synthèse arrivent par les événements de la session ; le résultat est rangé à la fin."""
    return await start_committee(rt, current.id, body)


@router.get("", response_model=list[CommitteeRunOut])
async def get_committees(
    current: CurrentUserDep,
    rt: ApplicationsDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[CommitteeRunOut]:
    """Les exécutions (d'une offre), la plus récente d'abord, chacune avec son avant et après ;
    une exécution dont la session s'est terminée sans résultat passe en `failed`."""
    return await list_runs(rt, current.id, posting_id)


@router.get(
    "/{run_id}",
    response_model=CommitteeRunOut,
    responses={404: {"description": "`committee_not_found`"}},
)
async def get_committee(
    run_id: Id, current: CurrentUserDep, rt: ApplicationsDep
) -> CommitteeRunOut:
    return await get_run(rt, current.id, run_id)
