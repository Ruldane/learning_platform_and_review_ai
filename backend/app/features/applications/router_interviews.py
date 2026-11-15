"""API des entretiens blancs (SPEC F10, D146) : lancement du parcours `interview` depuis une fiche
ou librement (offre ou intitulé seul), liste et détail (échanges, débrief, fiches de révision).
Toutes au nom de l'utilisatrice courante ; une 422 nomme les champs, sans jamais citer l'entrée."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.applications.router import ApplicationsDep, Id
from app.features.applications.schemas_interviews import (
    FreeInterviewIn,
    InterviewIn,
    InterviewOut,
    InterviewStartOut,
)
from app.features.applications.service.interviews import (
    get_interview,
    list_interviews,
    start_for_application,
    start_free,
)

router = APIRouter(tags=["interviews"], route_class=FieldPathsRoute)

_START: dict[int | str, dict[str, Any]] = {
    409: {
        "description": (
            "`interview_in_progress` (`details.interview_id` : l'entretien ouvert), "
            "`profile_required` (aucun profil maître validé)"
        )
    },
    503: {"description": "`engine_unavailable`"},
}


@router.post(
    "/applications/{application_id}/interviews",
    response_model=InterviewStartOut,
    status_code=202,
    responses={404: {"description": "`application_not_found`"}, **_START},
)
async def post_application_interview(
    application_id: Id, body: InterviewIn, current: CurrentUserDep, rt: ApplicationsDep
) -> InterviewStartOut:
    """Lance l'entretien blanc de la fiche : les questions arrivent par `interrupt.requested`
    (`kind` `interview_answer`), le débrief et les fiches de révision à la fin."""
    return await start_for_application(rt, current.id, application_id, body)


@router.post(
    "/interviews",
    response_model=InterviewStartOut,
    status_code=202,
    responses={404: {"description": "`posting_not_found`"}, **_START},
)
async def post_free_interview(
    body: FreeInterviewIn, current: CurrentUserDep, rt: ApplicationsDep
) -> InterviewStartOut:
    """Entretien libre, sans fiche : sur une offre (`posting_id`) ou sur un intitulé (`role`) ;
    rien n'est écrit au fil d'une candidature."""
    return await start_free(rt, current.id, body)


@router.get(
    "/interviews",
    response_model=list[InterviewOut],
    responses={404: {"description": "`application_not_found`"}},
)
async def get_interviews(
    current: CurrentUserDep,
    rt: ApplicationsDep,
    application_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[InterviewOut]:
    """Les entretiens (d'une fiche), le plus récent d'abord ; un entretien dont la session s'est
    terminée sans résultat passe en `failed`."""
    return await list_interviews(rt, current.id, application_id)


@router.get(
    "/interviews/{interview_id}",
    response_model=InterviewOut,
    responses={404: {"description": "`interview_not_found`"}},
)
async def get_one_interview(
    interview_id: Id, current: CurrentUserDep, rt: ApplicationsDep
) -> InterviewOut:
    return await get_interview(rt, current.id, interview_id)
