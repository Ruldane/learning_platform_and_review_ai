"""Postings API (SPEC F8, 14.2, D122). `POST /postings` adds a posting by its link or pasted
text and launches the analysis (`gap_analysis`); the same link or the same text returns the
existing posting (200, "certain" duplicate). Probable and possible duplicates arrive with the
analysis (`GET /postings/{id}`). The gap is read through `GET /postings/{id}/gap` (`gap`
feature)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from starlette.requests import HTTPConnection

from app.core.caller import CallerDep
from app.core.deps import CurrentUserDep, Db
from app.features.cv.service.runtime import CvRuntime
from app.features.postings.schemas import (
    DistinctIn,
    GapStarted,
    PostingCreatedOut,
    PostingDirectIn,
    PostingIn,
    PostingOut,
    PostingPatch,
    PostingSummaryOut,
)
from app.features.postings.service.create import create_posting
from app.features.postings.service.direct import create_direct, patch_direct
from app.features.postings.service.duplicates import mark_distinct
from app.features.postings.service.launch import relaunch
from app.features.postings.service.queries import delete_posting, list_postings, read_posting
from app.features.postings.service.runtime import PostingsRuntime

router = APIRouter(tags=["postings"])


def get_postings_runtime(conn: HTTPConnection) -> PostingsRuntime:
    """The postings opened by the lifespan (`app.state.career.postings`)."""
    runtime: PostingsRuntime = conn.app.state.career.postings
    return runtime


PostingsDep = Annotated[PostingsRuntime, Depends(get_postings_runtime)]


def get_cv_runtime(conn: HTTPConnection) -> CvRuntime:
    """The CV opened by the lifespan (`app.state.career.cv`): its reviews lock serves the
    deletion of a posting (D137 no. 7). Importing a service from another feature: allowed."""
    runtime: CvRuntime = conn.app.state.career.cv
    return runtime


CvDep = Annotated[CvRuntime, Depends(get_cv_runtime)]


@router.post(
    "/postings",
    response_model=PostingCreatedOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": PostingCreatedOut, "description": "Posting already added"}},
)
async def add_posting(
    body: PostingIn, current: CurrentUserDep, rt: PostingsDep, response: Response
) -> PostingCreatedOut:
    """201: posting created, analysis launched. 200: same link or same text, the existing posting
    (relaunched if it was refused, failed or interrupted). 422 `posting_source`,
    `posting_unreadable`, `posting_too_short`, `invalid_url`, `url_forbidden`: never the input
    in the response."""
    created = await create_posting(rt, current.id, body)
    if not created.created:
        response.status_code = status.HTTP_200_OK
    return created


@router.post(
    "/postings/direct",
    response_model=PostingCreatedOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": PostingCreatedOut, "description": "Posting already added"}},
)
async def write_posting(
    body: PostingDirectIn,
    current: CurrentUserDep,
    rt: PostingsDep,
    caller: CallerDep,
    response: Response,
) -> PostingCreatedOut:
    """Writes a posting directly: its text and its analysis are January's or Claude's, with no
    agent or model call (the gap is then launched through `POST /postings/{id}/gap`). 201:
    posting created, ready. 200: same link (or, without a link, same text), the existing
    posting. 422 `posting_too_short`, `posting_analysis_invalid`, `invalid_url`,
    `url_forbidden`: never the input in the response."""
    created = await create_direct(rt, current.id, body, is_mcp=caller.kind == "mcp")
    if not created.created:
        response.status_code = status.HTTP_200_OK
    return created


@router.patch(
    "/postings/{posting_id}",
    response_model=PostingOut,
    responses={
        404: {"description": "`posting_not_found`"},
        409: {"description": "`posting_not_analyzed`"},
        422: {"description": "`posting_analysis_invalid`"},
    },
)
async def patch_posting(
    posting_id: str,
    body: PostingPatch,
    current: CurrentUserDep,
    rt: PostingsDep,
    caller: CallerDep,
) -> PostingOut:
    """Edits the analysis of an analyzed posting (title, company, requirements, keywords...),
    without an agent: its memory and its duplicates are recomputed."""
    return await patch_direct(rt, current.id, posting_id, body, is_mcp=caller.kind == "mcp")


@router.get("/postings", response_model=list[PostingSummaryOut])
async def get_postings(current: CurrentUserDep, db: Db) -> list[PostingSummaryOut]:
    """January's postings, most recent first."""
    return await list_postings(db, current.id)


@router.get("/postings/{posting_id}", response_model=PostingOut)
async def get_posting(posting_id: str, current: CurrentUserDep, db: Db) -> PostingOut:
    return await read_posting(db, current.id, posting_id)


@router.delete(
    "/postings/{posting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "`posting_not_found`"},
        409: {
            "description": (
                "`review_in_progress` (a CV review of the posting is launched or proposed: "
                "finish it first), `analysis_in_progress` (the posting analysis is running: "
                "try again in a moment), `posting_has_application` (an application record "
                "cites the posting: `details.application_id`), `posting_has_running_work` (a "
                "committee or an interview in progress cites the posting: `details.kind`, "
                "`committee` or "
                "`interview`)"
            )
        },
    },
)
async def remove_posting(
    posting_id: str, current: CurrentUserDep, db: Db, rt: PostingsDep, cv: CvDep
) -> Response:
    """Removes the posting, its `posting` memory item, its reviews and versions (PDFs and
    images included); 409 `review_in_progress` or `analysis_in_progress` if one is running."""
    await delete_posting(db, rt.memory, cv.review_lock(current.id), current.id, posting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/postings/{posting_id}/distinct", status_code=status.HTTP_204_NO_CONTENT)
async def distinct_postings(
    posting_id: str, body: DistinctIn, current: CurrentUserDep, db: Db
) -> Response:
    """ "Distinct postings": the duplicate disappears on both sides."""
    await mark_distinct(db, current.id, posting_id, body.other_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/postings/{posting_id}/gap", response_model=GapStarted, status_code=status.HTTP_202_ACCEPTED
)
async def relaunch_gap(posting_id: str, current: CurrentUserDep, rt: PostingsDep) -> GapStarted:
    """Relaunches the gap analysis; 409 `gap_in_progress` if it is already running."""
    sid = await relaunch(rt, current.id, posting_id, if_needed=False)
    assert sid is not None  # without `if_needed`, a session is always launched
    return GapStarted(session_id=sid)
