"""Port de la revue d'un CV vu par le parcours `cv_review` (`CvReviewStore`, D129, D130).

`context` relit tout à chaque nœud (rien n'est gardé dans l'état du graphe) : l'offre et son
analyse, le profil **à la version figée dans la revue**, le CV d'origine composé dans l'ordre des
sections du gabarit figé (`base_content`), les indicateurs avant, l'entreprise et sa fiche
seulement si elle a moins de `BRIEF_MAX_AGE_DAYS` jours. Chaque écriture est idempotente :
`save_company` (fiche réécrite à l'identique, revue rattachée par sa session), `save_proposals`
(`(revue, référence)` unique), `render_version` (version déjà rendue relue), `close`.

Journaux : identifiants et nombres seulement (jamais une entreprise, un texte du CV ni de
l'offre)."""

import logging
from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_compose import base_content
from app.agents.tools.cv_indicators import Coverage, Indicators
from app.agents.tools.cv_review_port import (
    BRIEF_MAX_AGE_DAYS,
    ReviewContext,
    ReviewReport,
    VersionOutcome,
)
from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.agents.tools.cv_validator import Verdict
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import CompanyBrief, Proposal
from app.db.models.career import CvReview
from app.db.models.postings import Company
from app.features.cv.repository import (
    CompanyRepository,
    ModificationRepository,
    ProfileRepository,
    ReviewRepository,
    TemplateRepository,
)
from app.features.cv.service.generate import render_version
from app.features.cv.service.review_data import (
    indicators_of,
    review_not_found,
    target_text,
    template_order,
)
from app.features.cv.service.runtime import CvRuntime
from app.features.postings.service.queries import get_posting
from app.features.postings.service.rules import company_key
from app.features.postings.service.runtime import company_lock

logger = logging.getLogger(__name__)

AUTHORS = {"a": "ats_reader", "r": "recruiter"}
_NO_INDICATORS = Indicators(Coverage(covered=0, total=0, percent=100, missing=[]), [])


async def review_row(db: AsyncSession, user_id: str, review_id: str) -> CvReview:
    row = await ReviewRepository(db, user_id).get(review_id)
    if row is None:
        raise review_not_found()
    return row


async def frozen_base(
    db: AsyncSession, user_id: str, review: CvReview
) -> tuple[MasterProfileData, CvContent]:
    """Le profil figé dans la revue et le CV d'origine composé dans l'ordre du gabarit figé."""
    profile_row = await ProfileRepository(db, user_id).by_version(review.profile_version)
    if profile_row is None:
        raise review_not_found()
    profile = MasterProfileData.model_validate(profile_row.data)
    template = await TemplateRepository(db, user_id).get(review.template_id)
    order = template_order(template.spec if template is not None else None)
    return profile, base_content(profile, order)


def _fresh_brief(rt: CvRuntime, company: Company | None) -> CompanyBrief | None:
    if company is None or company.brief is None or company.refreshed_at is None:
        return None
    if rt.now() - company.refreshed_at >= timedelta(days=BRIEF_MAX_AGE_DAYS):
        return None
    return CompanyBrief.model_validate(company.brief)


class AgentCvReviewStore:
    """`CvReviewStore` de la composition (`app.bootstrap_career`)."""

    def __init__(self, runtime: CvRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, review_id: str) -> ReviewContext:
        async with self._rt.session_factory() as db:
            review = await review_row(db, user_id, review_id)
            posting = await get_posting(db, user_id, review.posting_id)
            profile, base = await frozen_base(db, user_id, review)
            analysis = (
                PostingAnalysis.model_validate(posting.analysis) if posting.analysis else None
            )
            name = posting.company or (analysis.company if analysis else None)
            company = (
                await CompanyRepository(db, user_id).by_key(company_key(name)) if name else None
            )
        return ReviewContext(
            review_id=review.id,
            posting_id=posting.id,
            analysis=analysis,
            posting_text=posting.text,
            posting_urls=[posting.url] if posting.url else [],
            profile=profile,
            base=base,
            before=indicators_of(review.before) if review.before else _NO_INDICATORS,
            company=name,
            company_brief=_fresh_brief(self._rt, company),
            company_ats=company.ats if company is not None else None,
        )

    async def save_company(
        self,
        user_id: str,
        session_id: str,
        name: str,
        brief: CompanyBrief,
        sources: Sequence[str],
        ats: str | None,
    ) -> None:
        key = company_key(name) or name.strip().casefold()
        lock = company_lock(self._rt.company_locks, user_id, key)
        async with lock, self._rt.session_factory() as db:
            repo = CompanyRepository(db, user_id)
            row = await repo.by_key(key) or await repo.add(name=name[:200], name_norm=key[:200])
            row.brief = brief.model_dump(mode="json")
            row.sources, row.ats, row.refreshed_at = list(sources)[:10], ats, self._rt.now()
            review = await ReviewRepository(db, user_id).by_session(session_id)
            if review is not None:
                review.company_id = row.id
            await db.commit()
            company_id = row.id
        logger.info("Fiche entreprise rangée : session %s, entreprise %s", session_id, company_id)

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        review_id: str,
        items: Sequence[tuple[Proposal, Verdict]],
        gap_terms: Sequence[str],
        report: ReviewReport,
    ) -> int:
        async with self._rt.session_factory() as db:
            review = await review_row(db, user_id, review_id)
            profile, base = await frozen_base(db, user_id, review)
            repo = ModificationRepository(db, user_id)
            known = {row.ref for row in await repo.of_review(review_id)}
            added = 0
            for proposal, verdict in items:
                if verdict.status == "to_gap" or proposal.ref in known:
                    continue  # un mot clé absent du profil n'entre jamais dans le CV
                known.add(proposal.ref)
                added += 1
                await repo.add(
                    review_id=review_id,
                    ref=proposal.ref,
                    section=proposal.section,
                    action=proposal.action,
                    target=proposal.target,
                    before=target_text(base, profile, proposal.target),
                    after=proposal.after,
                    reason=proposal.reason,
                    type=proposal.type,
                    fact_ids=list(proposal.fact_ids),
                    status="proposed" if verdict.status == "ok" else "to_confirm",
                    blocks=list(verdict.blocks),
                    author=AUTHORS.get(proposal.ref[:1], "recruiter"),
                )
            review.keywords_to_gap = list(dict.fromkeys([*review.keywords_to_gap, *gap_terms]))
            review.report = review.report or report.model_dump(mode="json")
            if review.status == "running":
                review.status = "proposed"
            await db.commit()
        logger.info(
            "Propositions rangées : session %s, revue %s, %d nouvelle(s), %d en tout",
            session_id,
            review_id,
            added,
            len(known),
        )
        return len(known)

    async def render_version(self, user_id: str, version_id: str) -> VersionOutcome:
        async with self._rt.session_factory() as db:
            return await render_version(self._rt, db, user_id, version_id)

    async def close(self, user_id: str, review_id: str) -> None:
        async with self._rt.review_lock(user_id), self._rt.session_factory() as db:
            review = await review_row(db, user_id, review_id)
            if review.status in ("running", "proposed"):
                review.status = "done"
                await db.commit()
        logger.info("Revue fermée : utilisateur %s, revue %s", user_id, review_id)
