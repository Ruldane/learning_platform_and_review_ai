"""API des revues de CV et des décisions de January (SPEC 5.3, 14.2 ; D130). `POST /cv/reviews`
fige le profil validé et le gabarit actif puis lance le parcours `cv_review` ; les décisions
(`PATCH /cv/modifications/{id}`, `PATCH /cv/reviews/{id}/modifications`) et « Générer le PDF »
(`POST /cv/reviews/{id}/generate`) passent par le verrou des revues. Une 422 nomme les champs,
jamais leur valeur."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status

from app.core.deps import CurrentUserDep
from app.features.cv.router.fields import FieldPathsRoute
from app.features.cv.router.profile import CvDep
from app.features.cv.schemas_reviews import (
    BulkDecision,
    BulkResult,
    CvReviewOut,
    ErrorOut,
    GenerateIn,
    GenerateStarted,
    ModificationOut,
    ModificationPatch,
    ReviewStart,
    ReviewStarted,
)
from app.features.cv.service.generate_start import generate
from app.features.cv.service.modifications import decide, decide_many
from app.features.cv.service.reviews import get_review, list_reviews, start_review

router = APIRouter(prefix="/cv", tags=["cv-reviews"], route_class=FieldPathsRoute)

Id = Annotated[str, Path(min_length=1, max_length=36)]


def errors(**by_status: str) -> dict[int | str, dict[str, Any]]:
    """Réponses d'erreur documentées : `{error: {code, message, details}}`, codes listés."""
    return {
        int(code.removeprefix("e")): {"model": ErrorOut, "description": text}
        for code, text in by_status.items()
    }


@router.post(
    "/reviews",
    response_model=ReviewStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=errors(
        e404="`posting_not_found`",
        e409=(
            "`posting_not_ready` (offre pas encore analysée), `profile_required` (aucun profil "
            "validé), `template_required` (aucun modèle actif prêt), `review_in_progress` "
            "(`details.review_id` : la revue en cours de cette offre)"
        ),
        e503="`engine_unavailable`",
    ),
)
async def post_review(body: ReviewStart, current: CurrentUserDep, rt: CvDep) -> ReviewStarted:
    """Lance la revue du CV contre l'offre ; le profil (sa version) et le gabarit sont figés."""
    return await start_review(rt, current.id, body.posting_id)


@router.get("/reviews", response_model=list[CvReviewOut])
async def get_reviews(
    current: CurrentUserDep,
    rt: CvDep,
    posting_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
) -> list[CvReviewOut]:
    """Les revues (d'une offre), la plus récente d'abord."""
    return await list_reviews(rt, current.id, posting_id)


@router.get(
    "/reviews/{review_id}",
    response_model=CvReviewOut,
    responses=errors(e404="`review_not_found`"),
)
async def get_one_review(review_id: Id, current: CurrentUserDep, rt: CvDep) -> CvReviewOut:
    return await get_review(rt, current.id, review_id)


@router.patch(
    "/reviews/{review_id}/modifications",
    response_model=BulkResult,
    responses=errors(e404="`review_not_found`", e409="`review_closed`"),
)
async def patch_modifications(
    review_id: Id, body: BulkDecision, current: CurrentUserDep, rt: CvDep
) -> BulkResult:
    """Décision groupée (50 au plus) ; les « à confirmer » ne sont jamais acceptés en groupe :
    ils reviennent dans `skipped`, avec les identifiants inconnus."""
    return await decide_many(rt, current.id, review_id, body)


@router.post(
    "/reviews/{review_id}/generate",
    response_model=GenerateStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=errors(
        e404="`review_not_found`",
        e409=(
            "`review_closed` (revue terminée ou en échec), `generation_in_progress` "
            "(`details.version_id` : la version en rendu), `review_not_waiting` (la revue "
            "n'attend pas « Que veux-tu maintenant ? »)"
        ),
        e503="`engine_unavailable`",
    ),
)
async def post_generate(
    review_id: Id, current: CurrentUserDep, rt: CvDep, body: GenerateIn | None = None
) -> GenerateStarted:
    """Crée la version (décisions figées au clic) et reprend la question de sortie ; le PDF se
    suit par `GET /cv/versions/{id}` (statut `rendering` puis `ready`, `pages_exceeded` ou
    `failed`) ou par l'événement `artifact.ready` de la session."""
    return await generate(rt, current.id, review_id, body or GenerateIn())


@router.patch(
    "/modifications/{modification_id}",
    response_model=ModificationOut,
    responses=errors(
        e404="`modification_not_found`",
        e409=(
            "`review_closed`, `confirmation_required` (« à confirmer » sans `confirm: true`), "
            "`fact_not_found` (le fait visé n'est plus dans le profil), `profile_conflict`, "
            "`profile_draft_pending` (un brouillon du profil attend sa validation : le valider "
            "avant de confirmer un fait)"
        ),
        e422=(
            "`validation_error` (`details.fields`), `keyword_not_in_profile` (le texte cite un "
            "mot clé de l'offre absent du profil) ; jamais la valeur reçue"
        ),
    ),
)
async def patch_modification(
    modification_id: Id, body: ModificationPatch, current: CurrentUserDep, rt: CvDep
) -> ModificationOut:
    """Accepte ou refuse ; `after` : texte réécrit, revalidé (il peut rester « à confirmer ») ;
    `confirm: true` : accepte une modification « à confirmer », son fait entre au profil maître
    (nouvelle version validée)."""
    return await decide(rt, current.id, modification_id, body)
