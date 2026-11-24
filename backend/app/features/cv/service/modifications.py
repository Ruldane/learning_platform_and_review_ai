"""Décisions de January sur les modifications d'une revue (SPEC 5.3 étape 7, 5.5 ; D128, D130).

- Refuser : toujours possible tant que la revue n'est pas terminée.
- Accepter : une modification « à confirmer » (`blocks` non vide : chiffre, outil, titre ou nom
  absent du profil) ne s'accepte qu'avec `confirm: true`, une par une ; le fait entre alors au
  profil maître (nouvelle version validée, `profile_facts`) et `blocks` est vidé.
- Texte réécrit par January (`after`, réécriture ou ajout seulement) : revalidé contre le profil
  figé dans la revue ; il peut devenir « à confirmer » ; un mot clé de l'offre absent du profil
  n'entre jamais dans le CV (422 `keyword_not_in_profile`, sans écho).
- En groupe : les « à confirmer » ne sont jamais acceptés (sautés et rendus dans `skipped`).

Après « Terminer » (ou l'échec de la revue) : 409 `review_closed`. Sous le verrou des revues : un
clic sur « Générer » fige les décisions d'un instant précis. Journaux : identifiants seulement."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_validator import validate
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.career import CvModification, CvReview
from app.features.cv.repository import ModificationRepository
from app.features.cv.schemas_reviews import (
    BulkDecision,
    BulkResult,
    ModificationOut,
    ModificationPatch,
)
from app.features.cv.service.generate_start import as_proposal
from app.features.cv.service.profile_facts import confirm_fact, invalid_after
from app.features.cv.service.review_data import (
    modification_not_found,
    modification_out,
    review_closed,
)
from app.features.cv.service.review_store import frozen_base, review_row
from app.features.cv.service.reviews import settle
from app.features.cv.service.runtime import CvRuntime
from app.features.postings.service.queries import get_posting

logger = logging.getLogger(__name__)

EDITABLE = ("rewrite", "add")


def confirmation_required() -> AppError:
    return AppError(
        "confirmation_required",
        "Confirm that the fact missing from your profile is true before accepting this edit.",
        409,
    )


def keyword_not_in_profile() -> AppError:
    return AppError(
        "keyword_not_in_profile",
        "This edit contains a posting keyword missing from your profile. "
        "It stays in the skill gap.",
        422,
        {"fields": ["after"]},
    )


def needs_confirmation(row: CvModification) -> bool:
    return row.status == "to_confirm" or bool(row.blocks)


async def _open_review(db: AsyncSession, user_id: str, review_id: str) -> CvReview:
    review = await review_row(db, user_id, review_id)
    if review.status != "proposed":
        raise review_closed()
    return review


async def _revalidate(
    db: AsyncSession, user_id: str, review: CvReview, row: CvModification, after: str
) -> bool:
    """Le texte de January remplace `after`, revalidé contre le profil figé (D128) ; vrai s'il
    est « à confirmer »."""
    if row.action not in EDITABLE:
        raise invalid_after()
    profile, _ = await frozen_base(db, user_id, review)
    posting = await get_posting(db, user_id, review.posting_id)
    analysis = PostingAnalysis.model_validate(posting.analysis)
    candidate = as_proposal(row).model_copy(update={"after": after})
    verdict = validate(candidate, profile, analysis)
    if verdict.status == "to_gap":
        raise keyword_not_in_profile()
    row.after, row.blocks = after, list(verdict.blocks)
    return verdict.status == "to_confirm"


async def _accept(
    rt: CvRuntime, db: AsyncSession, user_id: str, row: CvModification, body: ModificationPatch
) -> int | None:
    """Accepte, ou garde « à confirmer » un texte réécrit sans confirmation ; rend la version
    du profil écrite par une confirmation."""
    review = await _open_review(db, user_id, row.review_id)
    if body.after is not None:
        needs = await _revalidate(db, user_id, review, row, body.after.strip())
    else:
        needs = needs_confirmation(row)
    if needs and not body.confirm:
        if body.after is None:
            raise confirmation_required()
        row.status = "to_confirm"  # texte réécrit : gardé, à confirmer une par une
        return None
    confirmed = await confirm_fact(rt, user_id, row.target, row.after) if needs else None
    row.status, row.blocks = "accepted", []
    return confirmed


async def decide(
    rt: CvRuntime, user_id: str, modification_id: str, body: ModificationPatch
) -> ModificationOut:
    """Voir l'en-tête du module ; rend la modification telle qu'elle est rangée."""
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = await ModificationRepository(db, user_id).get(modification_id)
        if row is None:
            raise modification_not_found()
        if body.status == "accepted":
            confirmed = await _accept(rt, db, user_id, row, body)
        else:
            await _open_review(db, user_id, row.review_id)
            row.status, confirmed = "refused", None
        row.decided_at = rt.now()
        await db.commit()
        out = modification_out(row)
    logger.info(
        "Décision : utilisateur %s, modification %s, statut %s, profil confirmé %s",
        user_id,
        modification_id,
        out.status,
        confirmed,
    )
    return out


async def decide_many(
    rt: CvRuntime, user_id: str, review_id: str, body: BulkDecision
) -> BulkResult:
    """Décision groupée ; les « à confirmer » ne sont jamais acceptés en groupe."""
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        await _open_review(db, user_id, review_id)
        rows = {
            row.id: row for row in await ModificationRepository(db, user_id).of_review(review_id)
        }
        skipped: list[str] = []
        updated = 0
        for mod_id in dict.fromkeys(body.ids):
            row = rows.get(mod_id)
            if row is None or (body.status == "accepted" and needs_confirmation(row)):
                skipped.append(mod_id)
                continue
            row.status, row.decided_at = body.status, rt.now()
            updated += 1
        await db.commit()
    logger.info(
        "Décisions groupées : utilisateur %s, revue %s, %d appliquée(s), %d sautée(s)",
        user_id,
        review_id,
        updated,
        len(skipped),
    )
    return BulkResult(updated=updated, skipped=skipped)
