"""API du fil d'activité (SPEC 14.2, P15, P16, D163) : `GET /activity?after=&before=&limit=`, en
lecture seule, au nom de l'utilisatrice courante. La page relit toutes les 60 s avec `after`."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUserDep, Db
from app.features.activity.schemas import ActivityPage
from app.features.activity.service.feed import DEFAULT_LIMIT, activity_page

router = APIRouter(prefix="/activity", tags=["activity"])


def _utc(moment: datetime | None) -> datetime | None:
    return moment.replace(tzinfo=UTC) if moment is not None and moment.tzinfo is None else moment


@router.get("", response_model=ActivityPage)
async def get_activity(
    current: CurrentUserDep,
    db: Db,
    after: Annotated[
        datetime | None,
        Query(description="Ne rendre que les événements plus récents que cet instant."),
    ] = None,
    after_id: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Avec `after` : l'`id` du plus récent événement déjà vu. Le curseur est le couple "
                "`(at, id)` : les événements au même instant que lui ne sont pas perdus."
            ),
        ),
    ] = None,
    before: Annotated[
        datetime | None,
        Query(description="Ne rendre que les événements plus anciens que cet instant."),
    ] = None,
    before_id: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Avec `before` : l'`id` du plus ancien événement déjà vu (page suivante sans "
                "perte ni doublon, même à instant égal)."
            ),
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, description="Plafonné à 50.")] = DEFAULT_LIMIT,
) -> ActivityPage:
    """Les événements des agents et des tâches de fond, triés par `(at, id)` décroissant.
    Relecture : `after` = `latest_at` et `after_id` = `id` du premier événement de la page
    précédente. Page plus ancienne : `before` et `before_id` = `at` et `id` du dernier. Un `id`
    est stable (`{kind}:{ref}:{état}`) : le front ne montre jamais deux fois le même."""
    return await activity_page(
        db,
        current.id,
        after=_utc(after),
        before=_utc(before),
        after_id=after_id,
        before_id=before_id,
        limit=limit,
    )
