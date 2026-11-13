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

Le rattachement se fait sur le référentiel **existant** (revue 6.5, I2) : les compétences de
l'offre n'y entrent qu'après lui, par `save_gap`, et seulement celles restées sans rattachement.
Sinon chaque besoin trouverait son propre nom, sans niveau, au lieu de la notion de même sens que
January a déjà acquise.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.postings import GapMatch, GapResult, PostingStatus
from app.db.models.skills import LEVEL_ORDER, SkillLevel

MAX_KNOWN_SKILLS = 300  # noms du référentiel montrés au modèle
MAX_MATCHES = 40  # autant que de compétences dans une analyse
SKILL_NAME_MAX = 120  # `skills.name`, `SkillDraft.name` (revue 6.5, I1)

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
class KnownSkill:
    """Une compétence du référentiel de January et son niveau (`None` : sans niveau)."""

    name: str
    level: SkillLevel | None


def known_rank(skill: KnownSkill) -> int:
    """Ordre de `known_skills` : `prouve`, `valide`, `en_cours`, `declare`, puis sans niveau."""
    if skill.level is None:
        return len(LEVEL_ORDER)
    return len(LEVEL_ORDER) - 1 - LEVEL_ORDER.index(skill.level)


def ordered_known(skills: Sequence[KnownSkill]) -> list[KnownSkill]:
    """Les compétences acquises d'abord (ordre stable), `MAX_KNOWN_SKILLS` au plus : le plafond
    écarte d'abord les noms sans niveau."""
    return sorted(skills, key=known_rank)[:MAX_KNOWN_SKILLS]


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
    known: str | None = Field(default=None, max_length=SKILL_NAME_MAX)


class NeedMatch(BaseModel):
    """Réponse du modèle pour un besoin : son identifiant (`n3`) et celui de la compétence du
    référentiel (`k7`), ou `None`. Des identifiants, jamais des noms recopiés (revue 6.5, I3)."""

    need: str = Field(min_length=1, max_length=SKILL_NAME_MAX)
    known: str | None = Field(default=None, max_length=SKILL_NAME_MAX)


class SkillMatches(BaseModel):
    """Sortie structurée de l'Analyste en mode `match`."""

    items: list[NeedMatch] = Field(default_factory=list, max_length=MAX_MATCHES)


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
        `ready`, l'élément de mémoire `offre` indexé, et calcule les doublons probables et
        possibles. Les doublons sont rendus aussi quand `first` est faux (recalculés ou relus) :
        un rejeu après un arrêt les annonce encore. Les compétences de l'offre n'entrent **pas**
        au référentiel ici (voir `save_gap`)."""
        ...

    async def reject(self, user_id: str, posting_id: str, reason: str) -> None:
        """Statut `rejected` et sa raison ; idempotent."""
        ...

    async def known_skills(self, user_id: str) -> list[KnownSkill]:
        """Le référentiel **existant** de January, avec les niveaux (`user_skills`), dans l'ordre
        de `ordered_known` : `prouve`, `valide`, `en_cours`, `declare`, puis sans niveau ;
        `MAX_KNOWN_SKILLS` au plus, les compétences acquises gardées d'abord."""
        ...

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        """Idempotent par session : `gap` = `gap_result(session_id, matches)`. Les lignes sont
        calculées par le code (niveaux de `user_skills`, semaine du programme validé dont un
        module vise la compétence, `learnable` faux → `out_of_scope`), le score par
        `match_score`. Puis les besoins restés sans rattachement (`known` vide) entrent au
        référentiel (`upsert_catalog`, sans lien, sans niveau), après le rattachement."""
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

    async def known_skills(self, user_id: str) -> list[KnownSkill]:
        raise gap_unavailable()

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        raise gap_unavailable()


NO_GAP: GapStore = _NoGap()
