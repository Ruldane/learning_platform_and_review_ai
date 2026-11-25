"""Applications API (SPEC 6, D139): records (list, creation by hand or from a posting, detail,
edit), timeline (status change, note), duplicate check when a posting comes in, and indicators.
All on behalf of the current user; a 422 names the fields, without values; a duplicate 409
returns the existing records."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.applications.schemas import (
    ApplicationDetail,
    ApplicationIn,
    ApplicationOut,
    ApplicationPatch,
    ApplicationStatsOut,
    ApplicationStatus,
    CheckOut,
    CreatedOut,
    EventIn,
    IntakeIn,
    IntakeOut,
)
from app.features.applications.service.check import check_posting
from app.features.applications.service.create import create_application
from app.features.applications.service.events import add_event
from app.features.applications.service.intake import start_intake
from app.features.applications.service.queries import (
    list_applications,
    read_application,
    read_stats,
)
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.update import update_locked

router = APIRouter(prefix="/applications", tags=["applications"], route_class=FieldPathsRoute)

Id = Annotated[str, Path(min_length=1, max_length=36)]
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "`application_not_found`"}}


def get_applications_runtime(conn: HTTPConnection) -> ApplicationsRuntime:
    """The applications runtime opened by the lifespan (`app.state.career.applications`)."""
    runtime: ApplicationsRuntime = conn.app.state.career.applications
    return runtime


ApplicationsDep = Annotated[ApplicationsRuntime, Depends(get_applications_runtime)]


@router.get("", response_model=list[ApplicationOut])
async def get_applications(
    current: CurrentUserDep,
    db: Db,
    rt: ApplicationsDep,
    status: Annotated[ApplicationStatus | None, Query()] = None,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[ApplicationOut]:
    """The records, most recent first; adopts ready CV versions first."""
    return await list_applications(rt, db, current.id, status=status, posting_id=posting_id)


@router.post(
    "",
    response_model=CreatedOut,
    status_code=201,
    responses={
        404: {"description": "`posting_not_found`"},
        409: {
            "description": (
                "`application_duplicate` (`details.alerts`: the existing records that "
                "look like the posting), `application_exists` (`details.application_id`: "
                "a record already exists for this posting)"
            )
        },
    },
)
async def post_application(
    body: ApplicationIn, current: CurrentUserDep, rt: ApplicationsDep
) -> CreatedOut:
    """Creates the record; `info`: another record at the same company within 30 days."""
    return await create_application(rt, current.id, body)


@router.post(
    "/intake",
    response_model=IntakeOut,
    status_code=202,
    responses={409: {"description": "`intake_in_progress` (`details.session_id`)"}},
)
async def post_intake(body: IntakeIn, current: CurrentUserDep, rt: ApplicationsDep) -> IntakeOut:
    """Starts the Tracking Assistant on a sentence: the record being prepared is confirmed by
    January (question `application_confirm`) before it is created."""
    return IntakeOut(session_id=await start_intake(rt, current.id, body.text))


@router.get("/check", response_model=CheckOut, responses=_NOT_FOUND)
async def get_check(
    current: CurrentUserDep,
    db: Db,
    rt: ApplicationsDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
    url: Annotated[str | None, Query(min_length=1, max_length=2000)] = None,
) -> CheckOut:
    """Checks an incoming posting: by `posting_id` (the posting's record, the alerts) or by `url`
    (before analysis: "certain" only). Exactly one of the two inputs."""
    return await check_posting(db, current.id, rt.now(), posting_id, url)


@router.get("/stats", response_model=ApplicationStatsOut)
async def get_stats(current: CurrentUserDep, db: Db, rt: ApplicationsDep) -> ApplicationStatsOut:
    """Records by status, response rate and average response time, due follow-ups."""
    return await read_stats(rt, db, current.id)


@router.get("/{application_id}", response_model=ApplicationDetail, responses=_NOT_FOUND)
async def get_one_application(
    application_id: Id, current: CurrentUserDep, db: Db, rt: ApplicationsDep
) -> ApplicationDetail:
    return await read_application(db, current.id, rt.now(), application_id)


@router.patch("/{application_id}", response_model=ApplicationDetail, responses=_NOT_FOUND)
async def patch_application(
    application_id: Id, body: ApplicationPatch, current: CurrentUserDep, rt: ApplicationsDep
) -> ApplicationDetail:
    """Edits the fields sent; `contacts` replaces the list. The status only changes through
    `POST /applications/{id}/events`: sending it here is a 422."""
    return await update_locked(rt, current.id, application_id, body)


@router.post("/{application_id}/events", response_model=ApplicationDetail, responses=_NOT_FOUND)
async def post_event(
    application_id: Id, body: EventIn, current: CurrentUserDep, rt: ApplicationsDep
) -> ApplicationDetail:
    """A status change or a note, dated (today by default)."""
    return await add_event(rt, current.id, application_id, body)
