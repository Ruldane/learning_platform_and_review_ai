"""Port for the analysis of an offer and its gap (SPEC 5.3 step 1, F8, D121). `app.agents`
imports no feature (contract 6): it describes here what the `gap_analysis` graph needs
(the offer, the stored analysis, the refusal of a text that is not an offer, January's skills
reference, the stored gap); the `postings` feature implements it (`AgentGapStore`,
task 6.6).

The text of an offer is untrusted content (17.4): it is never logged, neither here nor by
the implementation.

Each write is idempotent, so that a node replayed after a stop (SPEC 9.4) writes nothing
plus :
- `save_analysis`: one analysis per offer, shared with the CV reviews; the first written
  wins (`UPDATE … WHERE analysis IS NULL`), the following ones reread the stored one;
- `reject`: a refused offer stays refused;
- `save_gap`: per session (`job_postings.gap.session_id`).

Matching is done against the **existing** reference (review 6.5, I2): the offer's skills
enter it only afterwards, through `save_gap`, and only those left unmatched.
Otherwise each need would get its own name, with no level, instead of the same-meaning concept
that January has already acquired.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.postings import GapMatch, GapResult, PostingStatus
from app.db.models.skills import LEVEL_ORDER, SkillLevel

MAX_KNOWN_SKILLS = 300  # names of the reference shown to the model
MAX_MATCHES = 40  # as many as the skills in an analysis
SKILL_NAME_MAX = 120  # `skills.name`, `SkillDraft.name` (revue 6.5, I1)

DuplicateLevel = Literal["certain", "probable", "possible"]


@dataclass(frozen=True)
class PostingView:
    """The offer as the graph reads it: `text` is the frozen copy read when it was added."""

    posting_id: str
    text: str
    url: str | None
    analysis: PostingAnalysis | None
    status: PostingStatus


@dataclass(frozen=True)
class DuplicateHit:
    """An already added offer that looks like this one. `certain`: same link or same text (at
    adding, 6.6); `probable`: same company, close title; `possible`: same company,
    close text (score of the best fragment, otherwise `None`). `created_at`: ISO 8601 (UTC)."""

    level: DuplicateLevel
    posting_id: str
    title: str | None
    company: str | None
    created_at: str
    score: float | None


@dataclass(frozen=True)
class KnownSkill:
    """A skill of January's reference and its level (`None`: no level)."""

    name: str
    level: SkillLevel | None


def known_rank(skill: KnownSkill) -> int:
    """Order of `known_skills`: `prouve`, `valide`, `en_cours`, `declare`, then without a level."""
    if skill.level is None:
        return len(LEVEL_ORDER)
    return len(LEVEL_ORDER) - 1 - LEVEL_ORDER.index(skill.level)


def ordered_known(skills: Sequence[KnownSkill]) -> list[KnownSkill]:
    """Acquired skills first (stable order), `MAX_KNOWN_SKILLS` at most: the cap
    drops the level-less names first."""
    return sorted(skills, key=known_rank)[:MAX_KNOWN_SKILLS]


@dataclass(frozen=True)
class AnalysisSaved:
    """The stored analysis (that of a faster session if `first` is false) and the duplicates
    computed after it (known company and title)."""

    posting_id: str
    analysis: PostingAnalysis
    duplicates: list[DuplicateHit]
    first: bool


class SkillMatch(BaseModel):
    """A need of the offer (`SkillNeed.name`) matched to a name of January's reference, or to
    nothing (`None`). A name outside the reference is never kept (D121 no. 3)."""

    need: str = Field(min_length=2, max_length=80)
    known: str | None = Field(default=None, max_length=SKILL_NAME_MAX)


class NeedMatch(BaseModel):
    """Model's answer for a need: its identifier (`n3`) and that of the reference skill
    (`k7`), or `None`. Identifiers, never copied names (review 6.5, I3)."""

    need: str = Field(min_length=1, max_length=SKILL_NAME_MAX)
    known: str | None = Field(default=None, max_length=SKILL_NAME_MAX)


class SkillMatches(BaseModel):
    """Structured output of the Analyst in `match` mode."""

    items: list[NeedMatch] = Field(default_factory=list, max_length=MAX_MATCHES)


@dataclass(frozen=True)
class GapSaved:
    """The stored gap: match score (`match_score`), number of rows, missing skills
    (unknown level, out of scope included) and, among them, the mandatory ones."""

    score: int
    rows: int
    missing: int
    missing_required: int


def gap_result(session_id: str, matches: Sequence[SkillMatch]) -> GapResult:
    """JSON shape of `job_postings.gap` (preflight G25): the matches and their session."""
    rows: list[GapMatch] = [{"need": m.need, "known": m.known} for m in matches]
    return {"session_id": session_id, "matches": rows}


def matches_of(gap: GapResult) -> list[SkillMatch]:
    return [SkillMatch(need=m["need"], known=m["known"]) for m in gap["matches"]]


class GapStore(Protocol):
    async def posting(self, user_id: str, posting_id: str) -> PostingView:
        """January's offer; 404 `posting_not_found` if it is not theirs."""
        ...

    async def save_analysis(
        self, user_id: str, session_id: str, posting_id: str, analysis: PostingAnalysis
    ) -> AnalysisSaved:
        """Idempotent and shared with `cv_review`: `UPDATE … WHERE analysis IS NULL`; an offer
        already analyzed is reread (`first` false). Sets the title, company (and key), and status
        `ready`, the indexed `offre` memory item, and computes the probable and possible duplicates.
        Duplicates are also returned when `first` is false (recomputed or reread):
        a replay after a stop still announces them. The offer's skills do **not** enter
        the reference here (see `save_gap`)."""
        ...

    async def reject(self, user_id: str, posting_id: str, reason: str) -> None:
        """`rejected` status and its reason; idempotent."""
        ...

    async def known_skills(self, user_id: str) -> list[KnownSkill]:
        """January's **existing** reference, with levels (`user_skills`), in the order
        of `ordered_known`: `prouve`, `valide`, `en_cours`, `declare`, then without a level;
        `MAX_KNOWN_SKILLS` at most, acquired skills kept first."""
        ...

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        """Idempotent per session: `gap` = `gap_result(session_id, matches)`. The rows are
        computed by the code (levels of `user_skills`, week of the validated program whose
        module targets the skill, `learnable` false -> `out_of_scope`), the score by
        `match_score`. Then the needs left unmatched (`known` empty) enter the
        reference (`upsert_catalog`, no link, no level), after the matching."""
        ...


def gap_unavailable() -> AppError:
    return AppError("gap_unavailable", "Posting analysis is unavailable in this runtime.", 503)


class _NoGap:
    """Engine default value (tests, starts without the feature)."""

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
