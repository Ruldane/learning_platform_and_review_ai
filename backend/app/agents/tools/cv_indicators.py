"""The two indicators of a CV against an offer (SPEC 5.3): coverage of the mandatory requirements
and ATS readability checks. No guarantee of passing is promised."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.agents.tools.cv_schema import CvLine
from app.agents.tools.posting_schema import Keyword, Requirement, contains_term, normalize_term

AtsCheckId = Literal[
    "selectable_text", "reading_order", "standard_headings", "contact_in_body", "font_sizes"
]


@dataclass(frozen=True)
class Coverage:
    """Mandatory requirements covered; `missing`: the text of those that are not."""

    covered: int
    total: int
    percent: int
    missing: list[str]


@dataclass(frozen=True)
class AtsCheck:
    id: AtsCheckId
    passed: bool
    detail: str


@dataclass(frozen=True)
class Indicators:
    coverage: Coverage
    checks: list[AtsCheck]


def _recoups(text: str, skills: set[str], form: str) -> bool:
    return contains_term(text, form, plural=True) or normalize_term(form, plural=True) in skills


def requirement_words(requirement: Requirement, keywords: Sequence[Keyword]) -> list[str]:
    """The words that cover a requirement: its skills, then the term and the variants of
    each keyword that overlaps it (one of its forms appears in the requirement or names one of its
    skills), simple plural ignored as in the coverage."""
    words = list(requirement.skills)
    skills = {normalize_term(skill, plural=True) for skill in requirement.skills}
    for keyword in keywords:
        forms = [keyword.term, *keyword.variants]
        if any(_recoups(requirement.text, skills, form) for form in forms):
            words.extend(forms)
    return list(dict.fromkeys(words))


def coverage(
    requirements: Sequence[Requirement],
    keywords: Sequence[Keyword],
    lines: Sequence[CvLine],
    *,
    backed_only: bool = True,
) -> Coverage:
    """A mandatory requirement is covered if one of its words (`requirement_words`) appears
    in a line backed by at least one fact (`fact_ids` non-empty); for the original CV,
    `backed_only=False`: all its lines count. Case, accents and simple plural ignored.
    A requirement without any word is never covered; no mandatory requirement: 100%."""
    texts = [
        f" {normalize_term(line.text, plural=True)} "
        for line in lines
        if line.fact_ids or not backed_only
    ]
    required = [requirement for requirement in requirements if requirement.required]
    missing: list[str] = []
    for requirement in required:
        needles = {normalize_term(w, plural=True) for w in requirement_words(requirement, keywords)}
        needles.discard("")
        if not any(f" {needle} " in text for needle in needles for text in texts):
            missing.append(requirement.text)
    covered = len(required) - len(missing)
    percent = 100 if not required else math.floor(100 * covered / len(required) + 0.5)
    return Coverage(covered=covered, total=len(required), percent=percent, missing=missing)
