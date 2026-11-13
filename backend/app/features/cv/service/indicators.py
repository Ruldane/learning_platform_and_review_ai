"""Les deux indicateurs d'un CV contre une offre (SPEC 5.3) : couverture des exigences
obligatoires et contrôles de lisibilité par un ATS. Aucune garantie de passage n'est promise."""

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
    """Exigences obligatoires couvertes ; `missing` : le texte de celles qui ne le sont pas."""

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
    """Les mots qui couvrent une exigence : ses compétences, puis le terme et les variantes de
    chaque mot clé qui la recoupe (une de ses formes figure dans l'exigence ou nomme une de ses
    compétences), pluriel simple ignoré comme dans la couverture."""
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
    """Une exigence obligatoire est couverte si l'un de ses mots (`requirement_words`) figure
    dans une ligne adossée à au moins un fait (`fact_ids` non vide) ; pour le CV d'origine,
    `backed_only=False` : toutes ses lignes comptent. Casse, accents et pluriel simple ignorés.
    Une exigence sans aucun mot n'est jamais couverte ; aucune exigence obligatoire : 100 %."""
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
