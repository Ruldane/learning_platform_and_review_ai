"""Mock interviews API (SPEC F10, D146): starts the `interview` flow from a record or freely
(posting or job title only), list and detail (exchanges, debrief, revision cards). All on
behalf of the current user; a 422 names the fields, never quoting the input."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.caller import MCP_IDENTITY
from app.core.deps import CurrentUserDep
from app.core.errors import AppError
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
from app.features.applications.service.system_design import start as start_system_design

router = APIRouter(tags=["interviews"], route_class=FieldPathsRoute)

_START: dict[int | str, dict[str, Any]] = {
    409: {
        "description": (
            "`interview_in_progress` (`details.interview_id`: the open interview), "
            "`profile_required` (no validated master profile), "
            "`radar_salary_missing` (no gross annual amount for the salary scenario)"
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
    """Starts the record's mock interview: questions arrive through `interrupt.requested`
    (`kind` `interview_answer`), the debrief and revision cards at the end."""
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
    """Free interview, without a record: on a posting (`posting_id`) or a job title (`role`);
    nothing is written to an application's timeline."""
    if body.system_design:
        if MCP_IDENTITY.get() is not None:
            raise AppError("interface_only", "This interview takes place in the interface.", 403)
        return await start_system_design(rt, current.id)
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
    """The interviews (of a record), most recent first; an interview whose session ended
    without a result turns `failed`."""
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
