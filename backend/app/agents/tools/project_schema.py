"""Schemas of the proof projects (P1 to P4, D165): the statement written by the Practitioner, its
evaluation and the four drafts in January's name. Nothing here decides a fact: the verdict, the
lengths and the honesty reference are code.

- `verdict`: "validated" only if **each** criterion from 1 to N has **a single** result and all
  are met; a missing, duplicated or out-of-range (outside 1 to N) result makes it "to redo".
  `settled_results` stores one result per criterion (a criterion without a single result is not
  met) for the port and for the closing sentence.
- `project_fact` / `project_reference` (P4): the project fact (statement title, January's
  description, module skills) added to the validated profile (or to an empty identity). The
  repository README never goes in: it is web text, not a fact from January. The description
  (4,000 characters at most) is cut into lines of at most 600 characters, the size of a profile
  fact: `text_claims` reads it in full.
- `draft_text`: the text that `text_claims` checks, for each draft.

The lines written by the model (criteria, constraints, name and achievements of the profile
entry) are brought down to **a single line** (`one_line`) before any check: a line break never
makes a fake numbered criterion, and a blank value is refused (retry) instead of being stored
then refused on reading. The texts read by January are shortened (`Prose`, `ShortenToMax`)
rather than refused (D97); the plan's word caps are set in characters (7.5 per word) in the
schema sent to the model; only the LinkedIn post is counted in words, by the code
(`linkedin_words`)."""

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.cv_schema import (
    Identity,
    Line,
    MasterProfileData,
    Project,
    SkillFact,
    assign_fact_ids,
)
from app.db.models.daily import DraftKind, DraftStatus

__all__ = [
    "DRAFT_KINDS",
    "LINKEDIN_WORDS",
    "NOT_ASSESSED",
    "CriterionResult",
    "DraftKind",
    "DraftStatus",
    "ProfileEntryDraft",
    "ProjectBrief",
    "ProjectDrafts",
    "ProjectEvaluation",
    "draft_text",
    "linkedin_words",
    "project_fact",
    "project_reference",
    "settled_results",
    "unmet_count",
    "verdict",
]

DRAFT_KINDS: tuple[DraftKind, ...] = ("cv_line", "profile_entry", "linkedin_post", "readme_plan")
LINKEDIN_WORDS = (80, 200)  # words of the LinkedIn post, counted by the code
NOT_ASSESSED = "This criterion wasn't assessed."
_LINE = 600  # size of a profile fact line (`Line.text`)
_DESCRIPTION = 4_800  # 8 lines of 600: the 4,000-character description fits in full
_MAX_LINES = 8  # `Project.achievements`


def one_line(value: object) -> object:
    """The text on a single line: blanks and line breaks brought down to one space."""
    return " ".join(value.split()) if isinstance(value, str) else value


def _stripped(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


Short = Annotated[
    str, Field(min_length=1, max_length=160), ShortenToMax(), BeforeValidator(one_line)
]
Criterion = Annotated[
    str, Field(min_length=1, max_length=200), ShortenToMax(), BeforeValidator(one_line)
]
Achievement = Annotated[
    str, Field(min_length=1, max_length=200), ShortenToMax(), BeforeValidator(one_line)
]
PlanStep = Annotated[str, Field(min_length=1, max_length=120), ShortenToMax()]


class ProjectBrief(BaseModel):
    """The statement of a mini project: 3 to 6 criteria a reviewer can check, 3 to 6 hours."""

    title: str = Field(min_length=3, max_length=120)
    context: Prose = Field(min_length=1, max_length=900)  # 120 words at most
    objective: Prose = Field(min_length=1, max_length=450)  # 60 words at most
    constraints: list[Short] = Field(min_length=2, max_length=5)
    criteria: list[Criterion] = Field(min_length=3, max_length=6)
    hours: int = Field(ge=3, le=6)
    deliverable: Literal["repo", "description", "either"]


class CriterionResult(BaseModel):
    index: int = Field(ge=1)  # rank of the criterion, from 1
    met: bool
    comment: Prose = Field(default="", max_length=300)


class ProjectEvaluation(BaseModel):
    results: list[CriterionResult] = Field(max_length=6)
    feedback: Prose = Field(min_length=1, max_length=1500)  # 200 words at most


class ProfileEntryDraft(BaseModel):
    """The project entry January can add to her profile (never without her click)."""

    name: Annotated[str, Field(min_length=1, max_length=120), BeforeValidator(one_line)]
    description: Annotated[
        str, Field(max_length=600), ShortenToMax(), BeforeValidator(_stripped)
    ] = ""
    achievements: list[Achievement] = Field(default_factory=list, max_length=4)


class ProjectDrafts(BaseModel):
    cv_line: Annotated[str, Field(min_length=1, max_length=200), ShortenToMax()]
    profile_entry: ProfileEntryDraft
    linkedin_post: Prose = Field(
        min_length=1, max_length=1800
    )  # 80 to 200 words, counted by the code
    readme_plan: list[PlanStep] = Field(min_length=5, max_length=10)


def linkedin_words(text: str) -> int:
    return len(text.split())


def _by_index(results: Sequence[CriterionResult]) -> dict[int, list[CriterionResult]]:
    found: dict[int, list[CriterionResult]] = {}
    for result in results:
        found.setdefault(result.index, []).append(result)
    return found


def verdict(
    criteria_count: int, results: Sequence[CriterionResult]
) -> Literal["validated", "to_redo"]:
    """ "validated": one result per criterion from 1 to N, all met, no rank outside 1 to N."""
    found = _by_index(results)
    if criteria_count < 1 or any(not 1 <= index <= criteria_count for index in found):
        return "to_redo"
    complete = all(
        len(found.get(index, [])) == 1 and found[index][0].met
        for index in range(1, criteria_count + 1)
    )
    return "validated" if complete else "to_redo"


def settled_results(
    criteria_count: int, results: Sequence[CriterionResult]
) -> list[CriterionResult]:
    """One result per criterion from 1 to N, in order: the model's if it is unique, otherwise
    "not assessed" (missing or duplicated); a rank outside 1 to N is dropped."""
    found = _by_index(results)
    return [
        found[index][0]
        if len(found.get(index, [])) == 1
        else CriterionResult(index=index, met=False, comment=NOT_ASSESSED)
        for index in range(1, criteria_count + 1)
    ]


def unmet_count(criteria_count: int, results: Sequence[CriterionResult]) -> int:
    """The criteria not met or without a single result, out of N."""
    return sum(not result.met for result in settled_results(criteria_count, results))


def draft_text(kind: DraftKind, drafts: ProjectDrafts) -> str:
    """The text of each draft, as `text_claims` checks it."""
    if kind == "cv_line":
        return drafts.cv_line
    if kind == "linkedin_post":
        return drafts.linkedin_post
    if kind == "readme_plan":
        return "\n".join(drafts.readme_plan)
    entry = drafts.profile_entry
    return "\n".join([entry.name, entry.description, *entry.achievements]).strip()


def _chunks(text: str, size: int) -> list[str]:
    """`text` in chunks of at most `size` characters, cut between two words."""
    chunks: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > size:  # a "word" longer than a line: cut short
            if current:
                chunks.append(current)
                current = ""
            chunks.append(word[:size])
            word = word[size:]
        if current and len(current) + 1 + len(word) > size:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


def project_fact(
    title: str, description: str | None, skills: Sequence[str], repo_url: str | None
) -> Project:
    """The project fact: the statement title, what January says about it (in lines of at most
    600 characters), then the module's skills. Without identifier (`project_reference`)."""
    pieces = _chunks((description or "")[:_DESCRIPTION], _LINE)
    names = [name for name in dict.fromkeys(skills) if name.strip()]
    lines = [Line(text=piece) for piece in pieces[1 : _MAX_LINES + 1]]
    if names and len(lines) < _MAX_LINES:
        lines.append(Line(text=f"Skills: {', '.join(names)}"[:_LINE]))
    return Project(
        name=title[:120],
        description=pieces[0] if pieces else "",
        link=repo_url[:300] if repo_url else None,
        achievements=lines,
        sources=["january"],
    )


def project_reference(
    profile: MasterProfileData | None, fact: Project, skills: Sequence[str]
) -> MasterProfileData:
    """What the drafts may say: the validated profile (or an empty identity), the
    project fact and the module's skills. The identifiers are assigned by the code."""
    base = profile or MasterProfileData(identity=Identity(name="January"))
    extra = [
        SkillFact(name=name[:80], sources=["january"])
        for name in dict.fromkeys(skills)
        if name.strip()
    ]
    merged = base.model_copy(
        update={"projects": [*base.projects, fact], "skills": [*base.skills, *extra]}
    )
    return assign_fact_ids(merged)
