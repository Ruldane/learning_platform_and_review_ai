"""Port de l'analyse d'une offre et de son écart (SPEC 5.3 étape 1, F8, D121). `app.agents`
n'importe aucune feature (contrat 6) : il décrit ici ce dont le parcours `gap_analysis` a besoin
(l'offre, l'analyse rangée, le refus d'un texte qui n'est pas une offre, le référentiel de
compétences de January, l'écart rangé) ; la feature `postings` l'implémente (`AgentGapStore`,
tâche 6.6).

Le texte d'une offre est un contenu non fiable (17.4) : il n'est jamais journalisé, ni ici ni par
l'implémentation.

Chaque écriture est idempotente, pour qu'un nœud rejoué après un arrêt (SPEC 9.4) n'écrive rien de
plus :
- `save_analysis` : une analyse par offre, partagée avec les revues de CV ; la première écrite
  gagne (`UPDATE … WHERE analysis IS NULL`), les suivantes relisent celle qui est rangée ;
- `reject` : une offre refusée le reste ;
- `save_gap` : par session (`job_postings.gap.session_id`).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.postings import GapMatch, GapResult, PostingStatus

MAX_KNOWN_SKILLS = 300  # noms du référentiel montrés au modèle
MAX_MATCHES = 40  # autant que de compétences dans une analyse

DuplicateLevel = Literal["certain", "probable", "possible"]


@dataclass(frozen=True)
class PostingView:
    """L'offre telle que le parcours la lit : `text` est la copie figée lue à l'ajout."""

    posting_id: str
    text: str
    url: str | None
    analysis: PostingAnalysis | None
    status: PostingStatus


@dataclass(frozen=True)
class DuplicateHit:
    """Une offre déjà ajoutée qui ressemble à celle-ci. `certain` : même lien ou même texte (à
    l'ajout, 6.6) ; `probable` : même entreprise, titre proche ; `possible` : même entreprise,
    texte proche (score du meilleur fragment, sinon `None`). `created_at` : ISO 8601 (UTC)."""

    level: DuplicateLevel
    posting_id: str
    title: str | None
    company: str | None
    created_at: str
    score: float | None


@dataclass(frozen=True)
class AnalysisSaved:
    """L'analyse rangée (celle d'une session plus rapide si `first` est faux) et les doublons
    calculés après elle (entreprise et titre connus)."""

    posting_id: str
    analysis: PostingAnalysis
    duplicates: list[DuplicateHit]
    first: bool


class SkillMatch(BaseModel):
    """Un besoin de l'offre (`SkillNeed.name`) rattaché à un nom du référentiel de January, ou à
    rien (`None`). Un nom hors du référentiel n'est jamais gardé (D121 n° 3)."""

    need: str = Field(min_length=2, max_length=80)
    known: str | None = Field(default=None, max_length=80)


class SkillMatches(BaseModel):
    """Sortie structurée de l'Analyste en mode `match`."""

    items: list[SkillMatch] = Field(default_factory=list, max_length=MAX_MATCHES)


@dataclass(frozen=True)
class GapSaved:
    """L'écart rangé : score de match (`match_score`), nombre de lignes, compétences absentes
    (niveau inconnu, hors périmètre compris) et, parmi elles, les obligatoires."""

    score: int
    rows: int
    missing: int
    missing_required: int


def gap_result(session_id: str, matches: Sequence[SkillMatch]) -> GapResult:
    """Forme JSON de `job_postings.gap` (preflight G25) : les rattachements et leur session."""
    rows: list[GapMatch] = [{"need": m.need, "known": m.known} for m in matches]
    return {"session_id": session_id, "matches": rows}


def matches_of(gap: GapResult) -> list[SkillMatch]:
    return [SkillMatch(need=m["need"], known=m["known"]) for m in gap["matches"]]


class GapStore(Protocol):
    async def posting(self, user_id: str, posting_id: str) -> PostingView:
        """L'offre de January ; 404 `posting_not_found` si elle n'est pas à elle."""
        ...

    async def save_analysis(
        self, user_id: str, session_id: str, posting_id: str, analysis: PostingAnalysis
    ) -> AnalysisSaved:
        """Idempotent et partagé avec `cv_review` : `UPDATE … WHERE analysis IS NULL` ; une offre
        déjà analysée est relue (`first` faux). Pose le titre, l'entreprise (et sa clé), le statut
        `ready`, l'élément de mémoire `offre` indexé, les doublons probables et possibles, et
        ajoute les compétences de l'offre au référentiel (`upsert_catalog`, sans lien)."""
        ...

    async def reject(self, user_id: str, posting_id: str, reason: str) -> None:
        """Statut `rejected` et sa raison ; idempotent."""
        ...

    async def known_skills(self, user_id: str) -> list[str]:
        """Les noms du référentiel de January (`MAX_KNOWN_SKILLS` au plus)."""
        ...

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        """Idempotent par session : `gap` = `gap_result(session_id, matches)`. Les lignes sont
        calculées par le code (niveaux de `user_skills`, semaine du programme validé dont un
        module vise la compétence, `learnable` faux → `out_of_scope`), le score par
        `match_score`."""
        ...


def gap_unavailable() -> AppError:
    return AppError("gap_unavailable", "L'analyse d'offre n'est pas branchée sur ce moteur.", 503)


class _NoGap:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def posting(self, user_id: str, posting_id: str) -> PostingView:
        raise gap_unavailable()

    async def save_analysis(
        self, user_id: str, session_id: str, posting_id: str, analysis: PostingAnalysis
    ) -> AnalysisSaved:
        raise gap_unavailable()

    async def reject(self, user_id: str, posting_id: str, reason: str) -> None:
        raise gap_unavailable()

    async def known_skills(self, user_id: str) -> list[str]:
        raise gap_unavailable()

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        raise gap_unavailable()


NO_GAP: GapStore = _NoGap()
