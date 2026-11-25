"""Analysis of a job posting (SPEC 5.3 step 1, F8): structured output of the Analyst, also read
by the gap, the CV review and its indicators. The engine imports no feature
(contract 6): these types and the normalisation of terms therefore live here.

`normalize_term` is the only normalisation of terms of phase 6 (preflight G32): keywords
present in the posting, coverage of the requirements, presence of the keywords in the CV, tool
terms of the validator. The features import it from here.
"""

import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.agents.runtime.prose import Prose
from app.core.skills import normalize_skill_name

# Anything that is neither a letter, a digit, "+" nor "#" (C++, C#) separates two words.
_SEPARATORS = re.compile(r"[^\w+#]|_")
_MIN_PLURAL_WORD = 4  # final "s" removed from words of at least 4 letters ("aws" stays)

Short = Annotated[str, Field(min_length=1, max_length=80)]
PostingLevel = Literal["junior", "mid_level", "senior", "lead", "unknown"]
# Enough text for a posting (the route of 6.6 and the Analyst apply the same bound).
MIN_POSTING_CHARS = 300
MIN_POSTING_WORDS = 50


def _read_checkpoint_level(value: object) -> object:
    """Normalize levels from sessions checkpointed before the English migration."""
    if value == "confirme":
        return "mid_level"
    if value == "inconnu":
        return "unknown"
    return value


CheckpointPostingLevel = Annotated[PostingLevel, BeforeValidator(_read_checkpoint_level)]


def enough_text(text: str) -> bool:
    """Enough text for a posting: at least 300 characters and 50 words."""
    stripped = text.strip()
    return len(stripped) >= MIN_POSTING_CHARS and len(stripped.split()) >= MIN_POSTING_WORDS


def normalize_term(text: str, *, plural: bool = False) -> str:
    """The text without case (`casefold`) or accents, punctuation turned into spaces, words
    separated by one space. `plural` also removes a word's final "s" (simple plural)."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
    words = _SEPARATORS.sub(" ", plain).split()
    if plural:
        words = [_singular(word) for word in words]
    return " ".join(words)


def _singular(word: str) -> str:
    if len(word) >= _MIN_PLURAL_WORD and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def contains_term(text: str, term: str, *, plural: bool = False) -> bool:
    """`term` appears in `text`, whole words, after `normalize_term` on both sides. A term
    that is empty after normalisation never appears."""
    needle = normalize_term(term, plural=plural)
    return bool(needle) and f" {needle} " in f" {normalize_term(text, plural=plural)} "


class Requirement(BaseModel):
    """A requirement of the posting; `skills`: the skills it asks for, named."""

    text: Prose = Field(min_length=3, max_length=300)
    required: bool
    skills: list[Short] = Field(default_factory=list, max_length=6)


class Keyword(BaseModel):
    """A keyword of the posting, in its exact wording (`term`); `variants`: its other
    forms (acronym, long form)."""

    term: str = Field(min_length=2, max_length=80)
    variants: list[Short] = Field(default_factory=list, max_length=5)


class Eliminatory(BaseModel):
    """An eliminatory criterion (years of experience, location, language, degree...)."""

    kind: Literal["experience_years", "location", "language", "degree", "other"]
    text: Prose = Field(min_length=3, max_length=200)


class SkillNeed(BaseModel):
    """A requested skill; `learnable` false: outside the scope of a program (driving licence,
    mother tongue...), it goes to "out of scope" in the gap."""

    name: str = Field(min_length=2, max_length=80)
    required: bool
    domain: str | None = Field(default=None, max_length=60)
    learnable: bool = True


class PostingAnalysis(BaseModel):
    is_job_posting: bool
    title: str = Field(min_length=2, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    level: CheckpointPostingLevel
    location: str | None = Field(default=None, max_length=120)
    remote: str | None = Field(default=None, max_length=60)
    language: str = Field(pattern=r"^[a-z]{2}$")
    requirements: list[Requirement] = Field(default_factory=list, max_length=40)
    keywords: list[Keyword] = Field(default_factory=list, max_length=40)
    eliminatory: list[Eliminatory] = Field(default_factory=list, max_length=10)
    tools: list[Short] = Field(default_factory=list, max_length=30)
    skills: list[SkillNeed] = Field(default_factory=list, max_length=40)
    apply_url: str | None = Field(default=None, max_length=2048)


def keyword_problems(analysis: PostingAnalysis, text: str) -> list[str]:
    """One English sentence, sent back to the model, per keyword that does not appear as is in
    the text of the posting (case, accents, spaces and punctuation ignored; whole words)."""
    return [
        f"The keyword “{keyword.term}” does not appear as is in the posting: "
        "copy it exactly as it is written, or remove it."
        for keyword in analysis.keywords
        if not contains_term(text, keyword.term)
    ]


def requirement_issues(analysis: PostingAnalysis) -> list[tuple[int, str]]:
    """`(rank of the requirement, English sentence)` per mandatory requirement that names no
    skill (without a skill, it would never be covered: review 6.2, m3) or that names a
    skill missing from `skills` (the gap and the coverage would speak of two lists). The
    sentence quotes nothing from the posting: only ranks (review 6.5, m2)."""
    needs = {normalize_skill_name(skill.name) for skill in analysis.skills}
    issues: list[tuple[int, str]] = []
    for rank, requirement in enumerate(analysis.requirements, start=1):
        if not requirement.required:
            continue
        if not requirement.skills:
            issues.append(
                (
                    rank,
                    f"Requirement no. {rank} is mandatory but names no skill: "
                    "add to its `skills` at least one skill it asks for.",
                )
            )
            continue
        absent = [
            str(position)
            for position, name in enumerate(requirement.skills, start=1)
            if normalize_skill_name(name) not in needs
        ]
        if absent:
            issues.append(
                (
                    rank,
                    f"Requirement no. {rank} names a skill missing from the analysis `skills` "
                    f"list (no. {', '.join(absent)} of its `skills`): add it to `skills` "
                    "under the same name, or correct it.",
                )
            )
    return issues


def requirement_problems(analysis: PostingAnalysis) -> list[str]:
    """The sentences of `requirement_issues`, alone."""
    return [sentence for _, sentence in requirement_issues(analysis)]
