"""What the ATS Reader and the Recruiter propose for a targeted CV (SPEC 5.3, F9): changes
stored by reference, the Recruiter's positions on the Reader's proposals, company sheet.
The engine imports no feature (contract 6): these types therefore live here.

A model only cites fact identifiers (`x1a2`); what the `after` text says is checked by the
validator (`cv_validator`), not here.
"""

from collections.abc import Sequence
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.cv_schema import (
    MasterProfileData,
    ModificationAction,
    ModificationType,
    SectionKey,
    facts_of,
    in_cv,
)

# An identifier of a profile fact (see the header of `cv_schema`): prefix by kind, then an
# **unbounded** number ("c100" is allowed), then optionally `a`/`d` and the child's number.
FACT_ID = r"^[xfcplkts]\d+([ad]\d+)?$"
FactId = Annotated[str, Field(pattern=FACT_ID)]
_SECTION_OF_PREFIX: dict[str, SectionKey] = {
    "t": "summary",
    "s": "summary",
    "x": "experience",
    "f": "education",
    "c": "skills",
    "p": "projects",
    "l": "languages",
    "k": "links",
}
_SECTIONS: tuple[str, ...] = get_args(SectionKey)


def section_of(fact_id: str) -> SectionKey | None:
    """The CV section that holds the fact (title and summary: "summary")."""
    return _SECTION_OF_PREFIX.get(fact_id[:1])


class Proposal(BaseModel):
    """A proposed change. `ref`: `a` ATS Reader, `r` Recruiter. `after`: the new
    text (empty for `remove`; for `move`, the key of the section before which `section` goes).
    """

    ref: str = Field(pattern=r"^[ar]\d{1,2}$")
    section: SectionKey
    action: ModificationAction
    target: str | None = Field(default=None, pattern=FACT_ID)
    after: str = Field(default="", max_length=600)
    reason: Prose = Field(min_length=1, max_length=300)
    type: ModificationType
    fact_ids: list[FactId] = Field(default_factory=list, max_length=6)


class ProposalList(BaseModel):
    items: list[Proposal] = Field(max_length=25)


_Note = Annotated[str, Field(max_length=300), ShortenToMax()]


class AtsReading(ProposalList):
    """Output of the ATS Reader (D129): its proposals and its notes on how the posting's ATS
    reads the CV (report, `ats_notes`)."""

    notes: list[_Note] = Field(default_factory=list, max_length=6)


class RecruiterReading(ProposalList):
    """Output of the Recruiter (D129): its proposals, the strengths and the risks of the CV
    against the posting (report)."""

    strengths: list[_Note] = Field(default_factory=list, max_length=5)
    risks: list[_Note] = Field(default_factory=list, max_length=5)


class Stance(BaseModel):
    """The Recruiter's position on one of the ATS Reader's proposals (`ref`: its own)."""

    ref: str
    stance: Literal["keep", "drop", "amend"]
    after: str | None = Field(default=None, max_length=600)
    reason: Prose = Field(min_length=1, max_length=300)


class Confrontation(BaseModel):
    stances: list[Stance] = Field(max_length=50)


class CompanyBrief(BaseModel):
    """Company sheet: what the posting says, nothing else."""

    summary: Prose = Field(min_length=1, max_length=800)
    values: list[Annotated[str, Field(max_length=120)]] = Field(max_length=6)
    stack: list[Annotated[str, Field(max_length=80)]] = Field(max_length=15)
    tone: str | None = Field(default=None, max_length=80)


def _target_problems(p: Proposal, facts: dict[str, str], cv_ids: set[str]) -> list[str]:
    ref = p.ref
    if p.action == "move":
        if p.after not in _SECTIONS or p.after == p.section:
            return [f"Proposal {ref} moves a section: `after` must be the key of another section."]
        return []
    if p.target is None:
        return [f"Proposal {ref} ({p.action}) must target a profile fact: fill in `target`."]
    if p.target not in facts:
        return [f"Proposal {ref} targets a fact that is not in the profile: correct `target`."]
    out: list[str] = []
    if section_of(p.target) != p.section:
        out.append(f"Proposal {ref} targets a fact of another section than `section`.")
    if p.action == "add" and p.target in cv_ids:
        out.append(f"Proposal {ref} adds a fact already in the CV: propose a rewording instead.")
    if p.action in ("remove", "rewrite") and p.target not in cv_ids:
        out.append(
            f"Proposal {ref} ({p.action}) targets a fact absent from the CV: "
            "propose an addition instead."
        )
    if p.action in ("add", "rewrite") and not p.after.strip():
        out.append(f"Proposal {ref} ({p.action}) has no text: fill in `after`.")
    return out


def proposal_problems(items: Sequence[Proposal], profile: MasterProfileData) -> list[str]:
    """One English sentence, sent back to the model, per defect: duplicate reference, unknown
    fact (`target` or `fact_ids`), `add` of a fact already in the CV, `remove` or `rewrite` of
    a fact absent from the CV, section that is not the fact's, missing text, `move` without a
    target section. No sentence copies the text of a proposal."""
    facts = facts_of(profile)
    cv_ids = in_cv(profile)
    problems: list[str] = []
    seen: set[str] = set()
    for p in items:
        if p.ref in seen:
            problems.append(f"Reference {p.ref} is used twice: one reference per proposal.")
        seen.add(p.ref)
        problems += _target_problems(p, facts, cv_ids)
        unknown = [fact for fact in p.fact_ids if fact not in facts]
        if unknown:
            problems.append(
                f"Proposal {p.ref} cites facts absent from the profile ({', '.join(unknown)}): "
                "remove them or correct their identifiers."
            )
    return problems
