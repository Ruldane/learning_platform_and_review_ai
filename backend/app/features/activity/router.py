"""Activity feed API (SPEC 14.2, P15, P16, D163): `GET /activity?after=&before=&limit=`, read-only,
on behalf of the current user. The page re-reads every 60 s with `after`."""

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
        Query(description="Only return events more recent than this instant."),
    ] = None,
    after_id: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "With `after`: the `id` of the most recent event already seen. The cursor is the "
                "`(at, id)` pair: events at the same instant as it are not lost."
            ),
        ),
    ] = None,
    before: Annotated[
        datetime | None,
        Query(description="Only return events older than this instant."),
    ] = None,
    before_id: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "With `before`: the `id` of the oldest event already seen (next page without "
                "loss or duplicate, even at an equal instant)."
            ),
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, description="Capped at 50.")] = DEFAULT_LIMIT,
) -> ActivityPage:
    """Agent and background-task events, sorted by `(at, id)` descending.
    Re-read: `after` = `latest_at` and `after_id` = the `id` of the first event of the previous
    page. Older page: `before` and `before_id` = the `at` and `id` of the last one. An `id` is
    stable (`{kind}:{ref}:{state}`): the front end never shows the same one twice."""
    return await activity_page(
        db,
        current.id,
        after=_utc(after),
        before=_utc(before),
        after_id=after_id,
        before_id=before_id,
        limit=limit,
    )
