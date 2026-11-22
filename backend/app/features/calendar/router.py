from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from starlette.requests import HTTPConnection

from app.core.deps import Db, InterfaceUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.calendar.schemas import (
    CalendarProposalOut,
    CalendarStatus,
    ConnectIn,
    OAuthLink,
    Selection,
    UpcomingEvent,
)
from app.features.calendar.service import oauth, proposals, upcoming
from app.features.calendar.service.runtime import CalendarRuntime

router = APIRouter(prefix="/calendar", tags=["calendar"], route_class=FieldPathsRoute)


def calendar_runtime(conn: HTTPConnection) -> CalendarRuntime:
    runtime: CalendarRuntime = conn.app.state.calendar
    return runtime


CalendarDep = Annotated[CalendarRuntime, Depends(calendar_runtime)]
PRIVATE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


@router.get("/connection")
async def connection(user: InterfaceUserDep, db: Db, rt: CalendarDep) -> CalendarStatus:
    return await oauth.status(rt, db, user.id)


@router.post("/connection")
async def connect(
    user: InterfaceUserDep, rt: CalendarDep, body: ConnectIn, response: Response
) -> OAuthLink:
    url, cookie = await oauth.start(rt, user.id, body.consent)
    response.headers.update(PRIVATE)
    response.set_cookie(
        oauth.OAUTH_COOKIE,
        cookie,
        max_age=oauth.STATE_SECONDS,
        path=oauth.COOKIE_PATH,
        secure=rt.secure,
        httponly=True,
        samesite="lax",
    )
    return OAuthLink(authorization_url=url)


@router.get("/callback", status_code=303, response_class=RedirectResponse)
async def callback(request: Request, user: InterfaceUserDep, rt: CalendarDep) -> RedirectResponse:
    connected = await oauth.finish(
        rt,
        user.id,
        request.query_params.get("state"),
        request.query_params.get("code"),
        request.cookies.get(oauth.OAUTH_COOKIE),
    )
    front: str = request.app.state.settings.frontend_url
    result = "connected" if connected else "error"
    response = RedirectResponse(
        f"{front.rstrip('/')}/reglages/agenda?agenda={result}", status_code=303, headers=PRIVATE
    )
    response.delete_cookie(
        oauth.OAUTH_COOKIE, path=oauth.COOKIE_PATH, secure=rt.secure, httponly=True, samesite="lax"
    )
    return response


@router.delete("/connection")
async def disconnect(user: InterfaceUserDep, rt: CalendarDep) -> CalendarStatus:
    return await oauth.disconnect(rt, user.id)


@router.post("/proposals", status_code=201)
async def propose(user: InterfaceUserDep, rt: CalendarDep, body: Selection) -> CalendarProposalOut:
    return await proposals.prepare(rt, user.id, body)


@router.post("/proposals/{proposal_id}/confirm")
async def confirm(user: InterfaceUserDep, rt: CalendarDep, proposal_id: str) -> CalendarProposalOut:
    return await proposals.confirm(rt, user.id, proposal_id)


@router.get("/upcoming")
async def next_event(
    user: InterfaceUserDep, rt: CalendarDep, response: Response
) -> UpcomingEvent | None:
    response.headers.update(PRIVATE)
    return await upcoming.next_event(rt, user.id)
