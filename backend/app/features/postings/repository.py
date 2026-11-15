"""Offres de January (D118, D122) : lecture par lien normalisé, par empreinte de texte, par
entreprise ou par élément de mémoire ; l'analyse posée une seule fois
(`UPDATE … WHERE analysis IS NULL`). Chaque requête filtre par `user_id`."""

import builtins
from collections.abc import Collection
from typing import Any

from sqlalchemy import func, literal_column, select, update

from app.db.models.applications import Application
from app.db.models.career import OPEN_REVIEW_STATUSES, CvReview, CvVersion
from app.db.models.postings import JobPosting
from app.db.repository import UserScopedRepository


class PostingRepository(UserScopedRepository[JobPosting]):
    model = JobPosting

    async def get_fresh(self, posting_id: str) -> JobPosting | None:
        """L'offre relue en base (jamais l'objet gardé par la session)."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.id == posting_id, JobPosting.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_url_norm(self, url_norm: str) -> JobPosting | None:
        stmt = select(JobPosting).where(
            JobPosting.user_id == self.user_id, JobPosting.url_norm == url_norm
        )
        return (await self.session.execute(stmt.execution_options(populate_existing=True))).scalar()

    async def by_text_hash(self, text_hash: str) -> JobPosting | None:
        """La plus ancienne offre de ce texte (texte collé d'abord, puis lien)."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.user_id == self.user_id, JobPosting.text_hash == text_hash)
            .order_by(JobPosting.url_norm.is_not(None), JobPosting.created_at)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent(self) -> builtins.list[JobPosting]:
        """Les offres de January, les plus récentes d'abord."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.user_id == self.user_id)
            .order_by(JobPosting.created_at.desc(), literal_column("rowid").desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def same_company(self, company_norm: str, exclude_id: str) -> builtins.list[JobPosting]:
        """Les autres offres de cette entreprise (clé `company_key`), les plus anciennes d'abord."""
        stmt = (
            select(JobPosting)
            .where(
                JobPosting.user_id == self.user_id,
                JobPosting.company_norm == company_norm,
                JobPosting.id != exclude_id,
            )
            .order_by(JobPosting.created_at, literal_column("rowid"))
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def by_ids(self, ids: Collection[str]) -> dict[str, JobPosting]:
        if not ids:
            return {}
        stmt = select(JobPosting).where(
            JobPosting.user_id == self.user_id, JobPosting.id.in_(builtins.list(ids))
        )
        return {row.id: row for row in (await self.session.execute(stmt)).scalars()}

    async def by_memory_items(self, item_ids: Collection[str]) -> builtins.list[JobPosting]:
        if not item_ids:
            return []
        stmt = select(JobPosting).where(
            JobPosting.user_id == self.user_id,
            JobPosting.memory_item_id.in_(builtins.list(item_ids)),
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def claim_analysis(self, posting_id: str, **fields: Any) -> bool:
        """Pose l'analyse et ses champs si l'offre n'en a pas encore ; vrai si c'est celle-ci
        (la première écrite gagne, D121)."""
        stmt = (
            update(JobPosting)
            .where(
                JobPosting.id == posting_id,
                JobPosting.user_id == self.user_id,
                JobPosting.analysis.is_(None),
            )
            .values(**fields)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))

    async def item_shared(self, item_id: str, exclude_id: str) -> bool:
        """Une autre offre renvoie-t-elle au même élément de mémoire (même texte) ?"""
        stmt = select(func.count()).where(
            JobPosting.user_id == self.user_id,
            JobPosting.memory_item_id == item_id,
            JobPosting.id != exclude_id,
        )
        return bool((await self.session.execute(stmt)).scalar_one())

    async def running_reviews(self, posting_id: str) -> int:
        """Les revues de CV de l'offre encore ouvertes (lancées ou proposées)."""
        stmt = select(func.count()).where(
            CvReview.user_id == self.user_id,
            CvReview.posting_id == posting_id,
            CvReview.status.in_(OPEN_REVIEW_STATUSES),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def version_files(self, posting_id: str) -> builtins.list[str]:
        """Les clés rangées des versions de CV de l'offre : PDF et images des pages."""
        stmt = select(CvVersion.storage_key, CvVersion.page_images).where(
            CvVersion.user_id == self.user_id, CvVersion.posting_id == posting_id
        )
        keys: builtins.list[str] = []
        for storage_key, images in (await self.session.execute(stmt)).all():
            keys += [key for key in (storage_key, *images) if isinstance(key, str) and key]
        return keys

    async def reviewed(self, posting_ids: Collection[str]) -> set[str]:
        """Les offres qui ont au moins une revue de CV."""
        if not posting_ids:
            return set()
        stmt = select(CvReview.posting_id).where(
            CvReview.user_id == self.user_id, CvReview.posting_id.in_(builtins.list(posting_ids))
        )
        return {row[0] for row in (await self.session.execute(stmt)).all()}

    async def application_id(self, posting_id: str) -> str | None:
        """La fiche de candidature qui cite l'offre, si elle existe (modèle seul : aucune
        importation de feature)."""
        stmt = (
            select(Application.id)
            .where(Application.user_id == self.user_id, Application.posting_id == posting_id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
