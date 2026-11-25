"""Port de la revue d'un CV contre une offre (SPEC 5.3, F9, D129). `app.agents` n'importe aucune
feature (contrat 6) : il décrit ici ce dont le parcours `cv_review` a besoin ; la feature `cv`
l'implémente (`AgentCvReviewStore`, tâche 6.14).

Le profil maître, le CV et le texte de l'offre sont des données personnelles ou non fiables
(17.2, 17.4) : jamais journalisés, ni ici ni par l'implémentation.

Chaque écriture est idempotente, pour qu'un nœud rejoué après un arrêt (SPEC 9.4) n'écrive rien de
plus :
- `save_company` : par `(utilisatrice, clé de l'entreprise, session)` ;
- `save_proposals` : `(revue, référence)` unique ; la revue passe en `proposed` ;
- `render_version` : une version déjà rendue est relue, jamais rendue deux fois ;
- `close` : la revue passe en `done`, une seule fois.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.prose import ShortenToMax
from app.agents.tools.cv_indicators import Indicators
from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.agents.tools.cv_validator import Verdict
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.review_schema import CompanyBrief, Proposal
from app.core.errors import AppError
from app.db.models.career import VersionStatus

BRIEF_MAX_AGE_DAYS = 30  # une fiche entreprise plus vieille est refaite par l'Éclaireur
ATS_UPDATES_MAX_AGE_DAYS = 60  # au-delà, le dernier rafraîchissement ATS n'est plus montré
ATS_UPDATES_MAX = 3

OutputChoice = Literal["report", "pdf", "finish"]
# Texte libre lu par January (raccourci, jamais refusé, D97).
Note = Annotated[str, Field(max_length=300), ShortenToMax()]


@dataclass(frozen=True)
class AtsUpdate:
    """Une source « kept » du dernier rafraîchissement du web sur les ATS (P14) : texte venu du
    web, donc non fiable (17.4) ; `published` : sa date si la page la donne."""

    title: str
    url: str
    summary: str
    published: str | None


@dataclass(frozen=True)
class ReviewContext:
    """Ce que la revue lit : l'offre (analyse rangée ou `None`), le profil validé figé dans la
    revue, le CV d'origine composé (`base_content`, ordre des sections du gabarit), les
    indicateurs avant, l'entreprise et sa fiche de moins de `BRIEF_MAX_AGE_DAYS` jours (sinon
    `None`) avec l'ATS déjà repéré pour elle (`company_ats`, écart au plan : sans lui, une fiche
    réutilisée perdrait l'ATS lu sur ses pages). `ats_updates` : les sources retenues de la dernière
    session `ats_refresh` terminée il y a moins de `ATS_UPDATES_MAX_AGE_DAYS` jours, 3 au plus."""

    review_id: str
    posting_id: str
    analysis: PostingAnalysis | None
    posting_text: str
    posting_urls: list[str]
    profile: MasterProfileData
    base: CvContent
    before: Indicators
    company: str | None
    company_brief: CompanyBrief | None
    company_ats: str | None = None
    ats_updates: list[AtsUpdate] = field(default_factory=list)


@dataclass(frozen=True)
class VersionOutcome:
    """Une version rendue : `pages_exceeded` quand le CV ciblé garde plus de pages que l'original
    (`original_page_count`, écart au plan : la phrase dite à January le cite)."""

    version_id: str
    status: VersionStatus
    page_count: int | None
    filename: str
    original_page_count: int = 1


class ReviewReport(BaseModel):
    """The review report: detected ATS and its notes, company sheet summary, strengths and
    risks seen by the Recruiter, and the posting's knockout criteria. It promises no
    guarantee of passing an ATS."""

    ats: str | None = Field(default=None, max_length=40)
    ats_notes: list[Note] = Field(default_factory=list, max_length=6)
    company_summary: str | None = Field(default=None, max_length=800)
    strengths: list[Note] = Field(default_factory=list, max_length=5)
    risks: list[Note] = Field(default_factory=list, max_length=5)
    eliminatory: list[Annotated[str, Field(max_length=300)]] = Field(
        default_factory=list, max_length=10
    )


class CvReviewStore(Protocol):
    async def context(self, user_id: str, review_id: str) -> ReviewContext:
        """La revue de January ; 404 `review_not_found` si elle n'est pas à elle. Lecture seule."""
        ...

    async def save_company(
        self,
        user_id: str,
        session_id: str,
        name: str,
        brief: CompanyBrief,
        sources: Sequence[str],
        ats: str | None,
    ) -> None:
        """Fiche de l'entreprise (`companies`, `refreshed_at`), rattachée à la revue ; idempotent
        par `(utilisatrice, clé de l'entreprise, session)`."""
        ...

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        review_id: str,
        items: Sequence[tuple[Proposal, Verdict]],
        gap_terms: Sequence[str],
        report: ReviewReport,
    ) -> int:
        """Les modifications (`proposed` si le verdict est `ok`, `to_confirm` sinon, avec ses
        `blocks`), les mots clés partis vers l'écart et le rapport ; la revue passe en
        `proposed`. Idempotent : `(revue, référence)` unique. Rend le nombre de modifications
        rangées pour la revue."""
        ...

    async def render_version(self, user_id: str, version_id: str) -> VersionOutcome:
        """Rend la version créée par la route (6.14) ; idempotent : déjà rendue, relue."""
        ...

    async def close(self, user_id: str, review_id: str) -> None:
        """La revue passe en `done` ; idempotent."""
        ...


def cv_review_unavailable() -> AppError:
    return AppError("cv_review_unavailable", "CV reviews are unavailable in this runtime.", 503)


class _NoCvReview:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def context(self, user_id: str, review_id: str) -> ReviewContext:
        raise cv_review_unavailable()

    async def save_company(
        self,
        user_id: str,
        session_id: str,
        name: str,
        brief: CompanyBrief,
        sources: Sequence[str],
        ats: str | None,
    ) -> None:
        raise cv_review_unavailable()

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        review_id: str,
        items: Sequence[tuple[Proposal, Verdict]],
        gap_terms: Sequence[str],
        report: ReviewReport,
    ) -> int:
        raise cv_review_unavailable()

    async def render_version(self, user_id: str, version_id: str) -> VersionOutcome:
        raise cv_review_unavailable()

    async def close(self, user_id: str, review_id: str) -> None:
        raise cv_review_unavailable()


NO_CV_REVIEW: CvReviewStore = _NoCvReview()
