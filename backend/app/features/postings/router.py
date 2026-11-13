"""API des offres (SPEC F8, 14.2, D122). `POST /postings` ajoute une offre par son lien ou son
texte collé et lance l'analyse (`gap_analysis`) ; le même lien ou le même texte rend l'offre
existante (200, doublon « certain »). Les doublons probables et possibles arrivent avec
l'analyse (`GET /postings/{id}`). L'écart se lit par `GET /postings/{id}/gap` (feature `gap`)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.postings.schemas import (
    DistinctIn,
    GapStarted,
    PostingCreatedOut,
    PostingIn,
    PostingOut,
    PostingSummaryOut,
)
from app.features.postings.service.create import create_posting
from app.features.postings.service.duplicates import mark_distinct
from app.features.postings.service.launch import relaunch
from app.features.postings.service.queries import delete_posting, list_postings, read_posting
from app.features.postings.service.runtime import PostingsRuntime

router = APIRouter(tags=["postings"])


def get_postings_runtime(conn: HTTPConnection) -> PostingsRuntime:
    """Les offres ouvertes par le lifespan (`app.state.career.postings`)."""
    runtime: PostingsRuntime = conn.app.state.career.postings
    return runtime


PostingsDep = Annotated[PostingsRuntime, Depends(get_postings_runtime)]


@router.post(
    "/postings",
    response_model=PostingCreatedOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": PostingCreatedOut, "description": "Offre déjà ajoutée"}},
)
async def add_posting(
    body: PostingIn, current: CurrentUserDep, rt: PostingsDep, response: Response
) -> PostingCreatedOut:
    """201 : offre créée, analyse lancée. 200 : même lien ou même texte, l'offre existante
    (relancée si elle était refusée, en échec ou interrompue). 422 `posting_source`,
    `posting_unreadable`, `posting_too_short`, `invalid_url`, `url_forbidden` : jamais l'entrée
    dans la réponse."""
    created = await create_posting(rt, current.id, body)
    if not created.created:
        response.status_code = status.HTTP_200_OK
    return created


@router.get("/postings", response_model=list[PostingSummaryOut])
async def get_postings(current: CurrentUserDep, db: Db) -> list[PostingSummaryOut]:
    """Les offres de January, les plus récentes d'abord."""
    return await list_postings(db, current.id)


@router.get("/postings/{posting_id}", response_model=PostingOut)
async def get_posting(posting_id: str, current: CurrentUserDep, db: Db) -> PostingOut:
    return await read_posting(db, current.id, posting_id)


@router.delete("/postings/{posting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_posting(
    posting_id: str, current: CurrentUserDep, db: Db, rt: PostingsDep
) -> Response:
    """Retire l'offre, son élément de mémoire `offre`, ses revues et versions ; 409
    `review_in_progress` si une revue de CV tourne."""
    await delete_posting(db, rt.memory, current.id, posting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/postings/{posting_id}/distinct", status_code=status.HTTP_204_NO_CONTENT)
async def distinct_postings(
    posting_id: str, body: DistinctIn, current: CurrentUserDep, db: Db
) -> Response:
    """« Offres distinctes » : le doublon disparaît des deux côtés."""
    await mark_distinct(db, current.id, posting_id, body.other_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/postings/{posting_id}/gap", response_model=GapStarted, status_code=status.HTTP_202_ACCEPTED
)
async def relaunch_gap(posting_id: str, current: CurrentUserDep, rt: PostingsDep) -> GapStarted:
    """Relance l'analyse d'écart ; 409 `gap_in_progress` si elle tourne déjà."""
    sid = await relaunch(rt, current.id, posting_id, if_needed=False)
    assert sid is not None  # sans `if_needed`, une session est toujours lancée
    return GapStarted(session_id=sid)
