"""Simulateur d'astreinte et son rapport soumis au responsable d'exploitation."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from app.core.deps import CurrentUserDep, Db, InterfaceUserDep, get_interface_user
from app.core.field_paths import FieldPathsRoute
from app.features.oncall.schemas import (
    DiagnosticView,
    IncidentCreate,
    IncidentSummary,
    IncidentView,
    OncallReportIn,
    OncallReviewStarted,
)
from app.features.oncall.service import OncallService
from app.features.oncall.service.report import launch_report

router = APIRouter(prefix="/oncall/incidents", tags=["oncall"], route_class=FieldPathsRoute)
Id = Annotated[str, Path(min_length=1, max_length=36)]
_INTERFACE = [Depends(get_interface_user)]


def _service(request: Request, db: Db, user: CurrentUserDep) -> OncallService:
    return OncallService(db, user.id, request.app.state.providers.sandbox)


Oncall = Annotated[OncallService, Depends(_service)]


@router.get("")
async def list_incidents(service: Oncall) -> list[IncidentSummary]:
    return await service.list()


@router.post("", status_code=201, dependencies=_INTERFACE)
async def create_incident(body: IncidentCreate, service: Oncall) -> IncidentView:
    return await service.create(body)


@router.get("/{incident_id}")
async def get_incident(incident_id: Id, service: Oncall) -> IncidentView:
    return await service.get(incident_id)


@router.post("/{incident_id}/advance", dependencies=_INTERFACE)
async def advance_incident(incident_id: Id, service: Oncall) -> IncidentView:
    return await service.advance(incident_id)


@router.post("/{incident_id}/events/{event_id}/observe", dependencies=_INTERFACE)
async def observe_event(incident_id: Id, event_id: Id, service: Oncall) -> IncidentView:
    return await service.observe(incident_id, event_id)


@router.post("/{incident_id}/diagnostic", status_code=202, dependencies=_INTERFACE)
async def diagnose_incident(incident_id: Id, service: Oncall) -> DiagnosticView:
    return await service.diagnose(incident_id)


@router.post("/{incident_id}/report", status_code=202)
async def submit_incident_report(
    incident_id: Id,
    body: OncallReportIn,
    request: Request,
    user: InterfaceUserDep,
) -> OncallReviewStarted:
    return await launch_report(request.app.state.launcher, user.id, incident_id, body.text)
