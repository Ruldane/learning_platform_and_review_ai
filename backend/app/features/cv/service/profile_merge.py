"""Identifiants des faits d'une nouvelle version du profil maître (D118, D124). Les modifications
des revues de CV citent ces ids : un fait inchangé garde le sien, un fait neuf reçoit un numéro
jamais pris par aucune version passée (`taken`), même si le fait qui le portait a disparu.

- brouillon de l'Archiviste : `merge_draft` reprend l'id d'un fait de la dernière version validée
  au même texte normalisé (rôle et entreprise, diplôme et école, nom, lien, texte d'une ligne ; une
  réalisation ou un détail sous le même parent), puis numérote le reste ;
- version de January : `keep_known` garde les ids déjà attribués (un fait modifié garde son id),
  efface les autres, puis numérote le reste ; un fait sans source vient d'elle (`january`)."""

import re
from collections.abc import Callable, Collection, Iterable, Sequence
from typing import Protocol

from app.agents.tools.cv_schema import (
    FactSource,
    Identity,
    Line,
    MasterProfileData,
    assign_fact_ids,
    facts_of,
)
from app.agents.tools.profile_check import plain


class _HasId(Protocol):
    id: str


class _Fact(Protocol):
    id: str
    sources: list[FactSource]


def all_ids(profiles: Iterable[MasterProfileData]) -> set[str]:
    """Tous les ids attribués par ces versions."""
    taken: set[str] = set()
    for profile in profiles:
        taken |= set(facts_of(profile))
    return taken


def _reuse[T: _HasId](
    items: Sequence[T], before: Sequence[T], key: Callable[[T], str]
) -> list[tuple[T, T]]:
    """Pose sur chaque élément l'id de l'ancien élément de même clé (chacun servi une fois), ""
    sinon ; rend les paires appariées."""
    pool: dict[str, list[T]] = {}
    for old in before:
        pool.setdefault(key(old), []).append(old)
    pairs: list[tuple[T, T]] = []
    for item in items:
        matches = pool.get(key(item))
        if matches:
            old = matches.pop(0)
            item.id = old.id
            pairs.append((item, old))
        else:
            item.id = ""
    return pairs


def _line_key(line: Line) -> str:
    return plain(line.text)


def _reuse_lines(pairs: Iterable[tuple[object, object]], field: str) -> None:
    """Réalisations ou détails : ids repris sous un même parent apparié."""
    for item, old in pairs:
        _reuse(getattr(item, field), getattr(old, field), _line_key)


def _children(profile: MasterProfileData) -> list[Line]:
    """Les réalisations et détails du profil."""
    lines = [line for x in profile.experiences for line in x.achievements]
    lines += [line for x in profile.education for line in x.details]
    return lines + [line for x in profile.projects for line in x.achievements]


def _clear_children(profile: MasterProfileData) -> None:
    for line in _children(profile):
        line.id = ""


def merge_draft(
    draft: MasterProfileData, previous: MasterProfileData | None, taken: Collection[str]
) -> MasterProfileData:
    """Le brouillon de l'Archiviste numéroté : ids de `previous` repris, les autres neufs."""
    out = draft.model_copy(deep=True)
    _clear_children(out)
    old = previous or MasterProfileData(identity=Identity(name="-"))
    _reuse([x for x in (out.title,) if x], [x for x in (old.title,) if x], _line_key)
    _reuse([x for x in (out.summary,) if x], [x for x in (old.summary,) if x], _line_key)
    jobs = _reuse(out.experiences, old.experiences, lambda x: plain(f"{x.role} {x.company}"))
    _reuse_lines(jobs, "achievements")
    schools = _reuse(out.education, old.education, lambda x: plain(f"{x.degree} {x.school}"))
    _reuse_lines(schools, "details")
    _reuse(out.skills, old.skills, lambda x: plain(x.name))
    _reuse_lines(_reuse(out.projects, old.projects, lambda x: plain(x.name)), "achievements")
    _reuse(out.languages, old.languages, lambda x: plain(x.name))
    _reuse(out.links, old.links, lambda x: plain(x.url))
    return number_new(out, taken)


def _keep(items: Iterable[_HasId], taken: Collection[str]) -> None:
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
    _keep([*facts, *_children(out)], taken)
    for fact in facts:
        if not fact.sources:
            fact.sources = ["january"]
    return number_new(out, taken)


def _number(items: Sequence[_HasId], prefix: str, taken: Collection[str]) -> None:
    """Garde les ids `<prefix><n>` bien formés et uniques ; numérote les autres au-dessus du plus
    grand numéro pris par `taken` ou par ces éléments."""
    pattern = re.compile(rf"^{re.escape(prefix)}([1-9]\d*)$")
    numbers = [m.group(1) for i in [*taken, *(x.id for x in items)] if (m := pattern.match(i))]
    top = max(map(int, numbers), default=0)
    seen: set[str] = set()
    fresh: list[_HasId] = []
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
