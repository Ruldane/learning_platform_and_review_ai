from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from starlette.requests import HTTPConnection

from app.core.deps import Db, InterfaceUserDep
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.features.portfolio.schemas import (
    LinkChoice,
    LinkTarget,
    PortfolioDraftOut,
    PublicationApproval,
    PublicationOut,
    SelectDraft,
    SiteOut,
    WithdrawalApproval,
)
from app.features.portfolio.service import artifacts, publication
from app.features.portfolio.service.render import CSP
from app.features.portfolio.service.runtime import PortfolioRuntime

router = APIRouter(tags=["portfolio"], route_class=FieldPathsRoute)
Slug = Annotated[str, Path(min_length=64, max_length=200, pattern=r"^[\w-]+={0,2}$")]
_HTML: dict[int | str, dict[str, Any]] = {
    200: {"content": {"text/html": {"schema": {"type": "string"}}}}
}
_ZIP: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}}
}


def _runtime(conn: HTTPConnection) -> PortfolioRuntime:
    rt: PortfolioRuntime = conn.app.state.portfolio
    return rt


Runtime = Annotated[PortfolioRuntime, Depends(_runtime)]


def _html(data: bytes, *, private: bool) -> Response:
    return Response(
        data,
        media_type="text/html",
        headers={
            "Cache-Control": "private, no-store" if private else "no-store",
            "Content-Security-Policy": f"{CSP}; sandbox; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/portfolio")
async def get_portfolio(user: InterfaceUserDep, db: Db, rt: Runtime) -> SiteOut:
    return await publication.read(db, user.id, rt.origin())


@router.post("/portfolio/drafts", status_code=201)
async def build_portfolio(
    body: SelectDraft, user: InterfaceUserDep, rt: Runtime
) -> PortfolioDraftOut:
    return await artifacts.build(rt, user.id, body)


@router.get("/portfolio/drafts/{draft_id}/preview", response_class=Response, responses=_HTML)
async def preview(draft_id: UUID, user: InterfaceUserDep, db: Db, rt: Runtime) -> Response:
    row = await artifacts.require_draft(db, user.id, str(draft_id))
    return _html(await artifacts.document(rt, row), private=True)


@router.get("/portfolio/drafts/{draft_id}/zip", response_class=Response, responses=_ZIP)
async def download(draft_id: UUID, user: InterfaceUserDep, db: Db, rt: Runtime) -> Response:
    row = await artifacts.require_draft(db, user.id, str(draft_id))
    return Response(
        await artifacts.document(rt, row, zipped=True),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="portfolio.zip"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/portfolio/publish")
async def publish(body: PublicationApproval, user: InterfaceUserDep, rt: Runtime) -> PublicationOut:
    return await publication.publish(rt, user.id, body)


@router.post("/portfolio/withdraw", status_code=200)
async def withdraw(body: WithdrawalApproval, user: InterfaceUserDep, rt: Runtime) -> None:
    await publication.withdraw(rt, user.id, body)


@router.put("/portfolio/links/{target}")
async def choose_link(
    target: LinkTarget, body: LinkChoice, user: InterfaceUserDep, rt: Runtime
) -> PublicationOut:
    return await publication.choose_link(rt, user.id, target, body)


@router.get("/public/portfolios/{slug}", response_class=Response, responses=_HTML)
async def public_portfolio(slug: Slug, request: Request, rt: Runtime) -> Response:
    try:
        data = await publication.public_document(rt, slug, request.url.netloc)
    except AppError as error:
        if error.status_code != 404:
            raise
        raise HTTPException(404, headers={"Cache-Control": "no-store"}) from None
    return _html(data, private=False)
