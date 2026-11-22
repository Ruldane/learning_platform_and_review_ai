from contextlib import suppress
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.portfolio_urls import public_url
from app.db.models.portfolio import PortfolioDraft, PortfolioSite
from app.features.portfolio.repository import Drafts, Sites
from app.features.portfolio.schemas import PortfolioDraftOut, SelectDraft
from app.features.portfolio.service.candidates import choices
from app.features.portfolio.service.render import archive, html
from app.features.portfolio.service.runtime import PortfolioRuntime
from app.providers.storage.base import StorageKeyInvalid


def missing() -> AppError:
    return AppError("portfolio_not_found", "Portfolio introuvable.", 404)


def draft_view(site: PortfolioSite, row: PortfolioDraft, origin: str | None) -> PortfolioDraftOut:
    return PortfolioDraftOut.model_validate(
        {
            "id": row.id,
            "digest": row.digest,
            "destination": public_url(origin, site.slug),
            "created_at": row.created_at,
        }
    )


async def require_draft(db: AsyncSession, user_id: str, draft_id: str) -> PortfolioDraft:
    draft = await Drafts(db, user_id).get(draft_id)
    if draft is None:
        raise missing()
    return draft


async def document(rt: PortfolioRuntime, row: PortfolioDraft, *, zipped: bool = False) -> bytes:
    try:
        data = await rt.storage.read(row.user_id, row.zip_key if zipped else row.html_key)
    except (FileNotFoundError, StorageKeyInvalid):
        raise missing() from None
    if not zipped and sha256(data).hexdigest() != row.digest:
        raise missing()
    return data


async def build(rt: PortfolioRuntime, user_id: str, requested: SelectDraft) -> PortfolioDraftOut:
    keys: list[str] = []
    async with rt.locks.get(user_id, "portfolio"), rt.factory() as db:
        available = await choices(db, user_id)
        selected = set(requested.selected)
        picked = [item for item in available if item.id in selected]
        if selected != {item.id for item in picked}:
            raise AppError(
                "portfolio_choices_changed", "Certains faits ont changé. Relis la sélection.", 409
            )
        data = html(picked)
        try:
            keys.append(await rt.storage.save(user_id, "portfolio", data, ".html"))
            keys.append(await rt.storage.save(user_id, "portfolio", archive(data), ".zip"))
            row = await Drafts(db, user_id).add(
                digest=sha256(data).hexdigest(), html_key=keys[0], zip_key=keys[1]
            )
            sites = Sites(db, user_id)
            site = await sites.for_owner()
            if site is None:
                site = await sites.add(slug=rt.cipher.encrypt("portfolio/" + user_id))
            site.draft_id = row.id
            await db.commit()
        except BaseException:
            for key in keys:
                with suppress(OSError, StorageKeyInvalid):
                    await rt.storage.delete(user_id, key)
            raise
        return draft_view(site, row, rt.origin())
