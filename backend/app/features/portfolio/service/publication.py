"""Approbation du contenu exact avant exposition, puis retrait par échange de pointeur."""

from hmac import compare_digest

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.portfolio_urls import matches_public_host, public_url
from app.core.security import SecretUnreadable
from app.db.base import utcnow
from app.db.models.portfolio import PortfolioSite
from app.features.portfolio.repository import Sites
from app.features.portfolio.schemas import (
    LinkChoice,
    LinkTarget,
    PublicationApproval,
    PublicationOut,
    SiteOut,
    WithdrawalApproval,
)
from app.features.portfolio.service.artifacts import document, draft_view, missing, require_draft
from app.features.portfolio.service.candidates import choices
from app.features.portfolio.service.runtime import PortfolioRuntime


def _changed() -> AppError:
    return AppError(
        "portfolio_version_changed",
        "La version ou la destination a changé. Relis le portfolio.",
        409,
    )


def _view(site: PortfolioSite, origin: str | None) -> PublicationOut | None:
    if not site.published_id or not site.published_url or site.published_at is None:
        return None
    available = site.published_url == public_url(origin, site.slug)
    return PublicationOut.model_validate(
        {
            "revision_id": site.published_id,
            "url": site.published_url,
            "published_at": site.published_at,
            "available": available,
            "use_in_cv": site.use_in_cv and available,
            "use_in_kit": site.use_in_kit and available,
        }
    )


async def read(db: AsyncSession, user_id: str, origin: str | None) -> SiteOut:
    site = await Sites(db, user_id).for_owner()
    draft = None
    if site is not None and site.draft_id is not None:
        draft = draft_view(site, await require_draft(db, user_id, site.draft_id), origin)
    return SiteOut(
        candidates=await choices(db, user_id),
        draft=draft,
        publication=_view(site, origin) if site is not None else None,
    )


async def publish(
    rt: PortfolioRuntime, user_id: str, approval: PublicationApproval
) -> PublicationOut:
    async with rt.locks.get(user_id, "portfolio"), rt.factory() as db:
        site = await Sites(db, user_id).for_owner()
        if site is None or site.draft_id != str(approval.draft_id):
            raise _changed()
        origin = rt.origin()
        destination = public_url(origin, site.slug)
        if destination is None:
            raise AppError("portfolio_host_unavailable", "Aucun hébergement public configuré.", 409)
        draft = await require_draft(db, user_id, site.draft_id)
        if destination != approval.destination or not compare_digest(draft.digest, approval.digest):
            raise _changed()
        await document(rt, draft)
        if site.published_id != draft.id or site.published_url != destination:
            site.published_id = draft.id
            site.published_url = destination
            site.published_at = utcnow()
            site.use_in_cv = site.use_in_kit = False
            await db.commit()
        result = _view(site, origin)
        assert result is not None
        return result


async def withdraw(rt: PortfolioRuntime, user_id: str, approval: WithdrawalApproval) -> None:
    async with rt.locks.get(user_id, "portfolio"), rt.factory() as db:
        site = await Sites(db, user_id).for_owner()
        if site is None or site.published_id is None:
            return
        if (
            site.published_id != str(approval.draft_id)
            or site.published_url != approval.destination
        ):
            raise _changed()
        if site.draft_id == site.published_id:
            site.draft_id = None
        site.published_id = site.published_url = site.published_at = None
        site.use_in_cv = site.use_in_kit = False
        await db.commit()


async def choose_link(
    rt: PortfolioRuntime, user_id: str, target: LinkTarget, choice: LinkChoice
) -> PublicationOut:
    async with rt.locks.get(user_id, "portfolio"), rt.factory() as db:
        site = await Sites(db, user_id).for_owner()
        origin = rt.origin()
        if (
            site is None
            or site.published_id != str(choice.revision_id)
            or site.published_url != choice.url
            or site.published_url != public_url(origin, site.slug)
        ):
            raise _changed()
        if target == "cv":
            site.use_in_cv = choice.enabled
        else:
            site.use_in_kit = choice.enabled
        await db.commit()
        result = _view(site, origin)
        assert result is not None
        return result


async def public_document(rt: PortfolioRuntime, slug: str, host: str) -> bytes:
    origin = rt.origin()
    if not matches_public_host(origin, host):
        raise missing()
    try:
        purpose, separator, user_id = rt.cipher.decrypt(slug).partition("/")
    except SecretUnreadable:
        raise missing() from None
    if purpose != "portfolio" or not separator or len(user_id) != 36:
        raise missing()
    async with rt.factory() as db:
        site = await Sites(db, user_id).for_owner()
        if (
            site is None
            or not compare_digest(site.slug, slug)
            or site.published_id is None
            or site.published_url != public_url(origin, slug)
        ):
            raise missing()
        return await document(rt, await require_draft(db, user_id, site.published_id))
