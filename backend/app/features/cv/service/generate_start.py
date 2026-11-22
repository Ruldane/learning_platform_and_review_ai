"""« Générer le PDF » (SPEC 5.3 ; D130) : une version par clic, décisions figées au clic, une
seule version en rendu à la fois.

Sous le verrou des revues : la revue doit être proposée (409 `review_closed` après « Terminer »
ou un échec, `review_not_waiting` sinon), aucune de ses versions en rendu (409
`generation_in_progress`) et sa session doit attendre la question de sortie (409
`review_not_waiting`). La version est créée (`rendering`, numéro suivant de l'offre, contenu
composé par le code à partir des modifications **acceptées à cet instant**, `decisions` : la
décision de chaque modification, `ignored` si une modification acceptée ne peut pas être
appliquée ou ferait perdre un lien ou une preuve de l'expérience), puis la question est reprise
avec `{"choice": "pdf", "version_id": …}`. Le parcours rend la version (`render_version`).
Une reprise refusée retire la version.

Journaux : identifiants et nombres ; jamais le nom du fichier ni un texte du CV."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import Proposal
from app.core.errors import AppError
from app.db.models.career import CvModification, CvReview, CvVersion
from app.features.cv.repository import (
    ModificationRepository,
    TemplateRepository,
    VersionRepository,
)
from app.features.cv.schemas_reviews import GenerateIn, GenerateStarted
from app.features.cv.service.generate import RENDER_FAILED
from app.features.cv.service.naming import cv_filename
from app.features.cv.service.review_data import posting_title, review_closed
from app.features.cv.service.review_store import frozen_base, review_row
from app.features.cv.service.reviews import settle, waiting_output
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.targeted_content import compose_targeted_cv
from app.features.portfolio.service.links import approved_link
from app.features.postings.service.queries import get_posting

logger = logging.getLogger(__name__)

_NOT_WAITING = ("stale_interrupt", "session_not_resumable", "interrupt_required")


def generation_in_progress(version_id: str) -> AppError:
    return AppError(
        "generation_in_progress",
        "Un PDF de cette revue est déjà en cours de génération : attends-le.",
        409,
        {"version_id": version_id},
    )


def review_not_waiting() -> AppError:
    return AppError(
        "review_not_waiting",
        "La revue n'attend pas encore ton choix : attends la question « Que veux-tu "
        "maintenant ? ».",
        409,
    )


def as_proposal(row: CvModification) -> Proposal:
    return Proposal(
        ref=row.ref,
        section=row.section,  # type: ignore[arg-type]  # colonne texte, valeurs de SectionKey
        action=row.action,  # type: ignore[arg-type]  # valeurs de ModificationAction
        target=row.target,
        after=row.after,
        reason=row.reason,
        type=row.type,  # type: ignore[arg-type]  # valeurs de ModificationType
        fact_ids=list(row.fact_ids),
    )


async def _new_version(
    db: AsyncSession,
    user_id: str,
    review: CvReview,
    allow_extra: bool,
    portfolio_origin: str | None,
) -> CvVersion:
    """La version figée au clic : contenu composé et décisions de cet instant."""
    profile, base = await frozen_base(db, user_id, review)
    posting = await get_posting(db, user_id, review.posting_id)
    analysis = PostingAnalysis.model_validate(posting.analysis) if posting.analysis else None
    company = posting.company or (analysis.company if analysis else None)
    title = (analysis.title if analysis else None) or posting.title
    mods = await ModificationRepository(db, user_id).of_review(review.id)
    accepted = [as_proposal(m) for m in mods if m.status == "accepted"]
    portfolio = await approved_link(db, user_id, "cv", portfolio_origin)
    applied = compose_targeted_cv(base, profile, accepted, analysis, portfolio=portfolio)
    decisions = {m.ref: m.status for m in mods} | dict.fromkeys(applied.ignored, "ignored")
    template = await TemplateRepository(db, user_id).get(review.template_id)
    versions = VersionRepository(db, user_id)
    return await versions.add(
        review_id=review.id,
        posting_id=review.posting_id,
        template_id=review.template_id,
        number=await versions.next_number(review.posting_id),
        status="rendering",
        content=applied.content.model_dump(mode="json"),
        decisions=decisions,
        filename=cv_filename(profile.identity.name, company, posting_title(title)),
        original_page_count=template.page_count if template is not None else 1,
        allow_extra_pages=allow_extra,
    )


async def _checked(db: AsyncSession, user_id: str, review_id: str) -> tuple[CvReview, str]:
    """La revue, et l'`interrupt_id` de la question de sortie qu'elle attend."""
    await settle(db, user_id)
    review = await review_row(db, user_id, review_id)
    if review.status not in ("running", "proposed"):
        raise review_closed()
    interrupt_id = await waiting_output(db, user_id, review)
    rendering = await VersionRepository(db, user_id).rendering([review.id])
    if rendering and interrupt_id is not None:
        # Le rendu ne tourne que session `running` : une version `rendering` alors que la session
        # attend la question de sortie est restée là (processus mort entre son enregistrement et
        # la reprise) ; elle ne bloque plus « Générer » (revue 6.14, M-1).
        for stale in rendering:
            stale.status, stale.failure_reason = "failed", RENDER_FAILED
        await db.commit()
        logger.info("Version restée en rendu : utilisateur %s, revue %s", user_id, review.id)
        rendering = []
    if rendering:
        raise generation_in_progress(rendering[0].id)
    if interrupt_id is None or review.session_id is None:
        raise review_not_waiting()
    return review, interrupt_id


async def _forget(rt: CvRuntime, user_id: str, version_id: str) -> None:
    async with rt.session_factory() as db:
        await VersionRepository(db, user_id).delete(version_id)
        await db.commit()


async def generate(
    rt: CvRuntime, user_id: str, review_id: str, body: GenerateIn
) -> GenerateStarted:
    """Voir l'en-tête du module."""
    async with rt.review_lock(user_id):
        async with rt.session_factory() as db:
            review, interrupt_id = await _checked(db, user_id, review_id)
            version = await _new_version(
                db, user_id, review, body.allow_extra_pages, rt.portfolio_origin()
            )
            await db.commit()  # le parcours relit la version dans sa propre session
            version_id, session_id, number = version.id, str(review.session_id), version.number
        value = {"choice": "pdf", "version_id": version_id}
        try:
            await rt.resumer.resume(user_id, session_id, interrupt_id, value)
        except BaseException as exc:
            await _forget(rt, user_id, version_id)
            if isinstance(exc, AppError) and exc.code in _NOT_WAITING:
                raise review_not_waiting() from None
            raise
    logger.info(
        "Génération demandée : utilisateur %s, revue %s, version %s (n° %d), session %s",
        user_id,
        review_id,
        version_id,
        number,
        session_id,
    )
    return GenerateStarted(version_id=version_id)
