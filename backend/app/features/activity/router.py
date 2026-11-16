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
    after: Annotated[datetime | None, Query()] = None,
    before: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, description="Plafonné à 50.")] = DEFAULT_LIMIT,
) -> ActivityPage:
    """Les événements des agents et des tâches de fond, le plus récent d'abord : `after` ne rend
    que les plus récents, `before` pagine vers les plus anciens."""
    return await activity_page(db, current.id, after=_utc(after), before=_utc(before), limit=limit)
