from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.contributions.schemas import (
    ContributionOut,
    CreateContribution,
    PublicationIn,
    PullIn,
    SuggestionsOut,
)
from app.features.contributions.service import dossiers
from app.features.contributions.service.discovery import suggestions
from app.features.contributions.service.runtime import ContributionRuntime
from app.features.contributions.service.tracking import track
from app.features.contributions.service.views import suggested

router = APIRouter(prefix="/contributions", tags=["contributions"])


def get_runtime(conn: HTTPConnection) -> ContributionRuntime:
    runtime: ContributionRuntime = conn.app.state.contributions
    return runtime


RuntimeDep = Annotated[ContributionRuntime, Depends(get_runtime)]


@router.get("/suggestions", response_model=SuggestionsOut)
async def propose_issues(
    current: CurrentUserDep, runtime: RuntimeDep, program_id: Annotated[str, Query(max_length=64)]
) -> SuggestionsOut:
    chapter, items = await suggestions(
        runtime.session_factory, runtime.github, current.id, program_id
    )
    return SuggestionsOut(
        chapter=chapter.title if chapter else None, items=[suggested(item) for item in items]
    )


@router.get("", response_model=list[ContributionOut])
async def list_contributions(current: CurrentUserDep, db: Db) -> list[ContributionOut]:
    return await dossiers.list_dossiers(db, current.id)


@router.post("", response_model=ContributionOut, status_code=201)
async def create_contribution(
    current: CurrentUserDep, runtime: RuntimeDep, body: CreateContribution
) -> ContributionOut:
    return await dossiers.create_dossier(runtime, current.id, body)


@router.get("/{contribution_id}", response_model=ContributionOut)
async def read_contribution(
    contribution_id: str, current: CurrentUserDep, db: Db
) -> ContributionOut:
    return await dossiers.get_dossier(db, current.id, contribution_id)


@router.post("/{contribution_id}/publication", response_model=ContributionOut)
async def prepare_publication(
    contribution_id: str, current: CurrentUserDep, db: Db, body: PublicationIn
) -> ContributionOut:
    return await dossiers.approve_publication(db, current.id, contribution_id, body)


@router.post("/{contribution_id}/pull", response_model=ContributionOut)
async def track_pull(
    contribution_id: str, current: CurrentUserDep, runtime: RuntimeDep, body: PullIn
) -> ContributionOut:
    return await track(runtime, current.id, contribution_id, body.url)


@router.post("/{contribution_id}/refresh", response_model=ContributionOut)
async def refresh_pull(
    contribution_id: str, current: CurrentUserDep, runtime: RuntimeDep
) -> ContributionOut:
    return await track(runtime, current.id, contribution_id, None)
