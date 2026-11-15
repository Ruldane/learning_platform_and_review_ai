"""Numérotation des faits du profil maître (D118, D124) : `keep_known` pour la version de
January (ids déjà attribués gardés, les autres effacés), `number_new` pour tout id neuf, numéroté
au-dessus de tout numéro déjà pris par une version passée. Utilisé par `profile_merge`."""

import re
from collections.abc import Collection, Iterable, Sequence
from typing import Protocol

from app.agents.tools.cv_schema import FactSource, Line, MasterProfileData, assign_fact_ids


class HasId(Protocol):
    id: str


class _Fact(Protocol):
    id: str
    sources: list[FactSource]


def children(profile: MasterProfileData) -> list[Line]:
    """Les réalisations et détails du profil."""
    lines = [line for x in profile.experiences for line in x.achievements]
    lines += [line for x in profile.education for line in x.details]
    return lines + [line for x in profile.projects for line in x.achievements]


def _keep(items: Iterable[HasId], taken: Collection[str]) -> None:
    for item in items:
        if item.id not in taken:
            item.id = ""


def keep_known(profile: MasterProfileData, taken: Collection[str]) -> MasterProfileData:
    """La version de January numérotée : un id déjà attribué reste (le fait a pu changer de
    texte), un id inconnu est effacé ; un fait sans source reçoit `january`."""
    out = profile.model_copy(deep=True)
    heads = [line for line in (out.title, out.summary) if line is not None]
    facts: list[_Fact] = [
        *heads,
        *out.experiences,
        *out.education,
        *out.skills,
        *out.projects,
        *out.languages,
        *out.links,
    ]
    _keep([*facts, *children(out)], taken)
    for fact in facts:
        if not fact.sources:
            fact.sources = ["january"]
    return number_new(out, taken)


def _number(items: Sequence[HasId], prefix: str, taken: Collection[str]) -> None:
    """Garde les ids `<prefix><n>` bien formés et uniques ; numérote les autres au-dessus du plus
    grand numéro pris par `taken` ou par ces éléments."""
    pattern = re.compile(rf"^{re.escape(prefix)}([1-9]\d*)$")
    numbers = [m.group(1) for i in [*taken, *(x.id for x in items)] if (m := pattern.match(i))]
    top = max(map(int, numbers), default=0)
    seen: set[str] = set()
    fresh: list[HasId] = []
    for item in items:
        if pattern.match(item.id) is None or item.id in seen:
            fresh.append(item)
        else:
            seen.add(item.id)
    for item in fresh:
        top += 1
        item.id = f"{prefix}{top}"


def number_new(profile: MasterProfileData, taken: Collection[str]) -> MasterProfileData:
    """Ids neufs au-dessus de tout numéro déjà pris (parents d'abord, puis leurs enfants)."""
    out = profile.model_copy(deep=True)
    _number([x for x in (out.title,) if x], "t", taken)
    _number([x for x in (out.summary,) if x], "s", taken)
    _number(out.experiences, "x", taken)
    for experience in out.experiences:
        _number(experience.achievements, f"{experience.id}a", taken)
    _number(out.education, "f", taken)
    for education in out.education:
        _number(education.details, f"{education.id}d", taken)
    _number(out.skills, "c", taken)
    _number(out.projects, "p", taken)
    for project in out.projects:
        _number(project.achievements, f"{project.id}a", taken)
    _number(out.languages, "l", taken)
    _number(out.links, "k", taken)
    return assign_fact_ids(out)  # filet : tout id est déjà bien formé et unique
