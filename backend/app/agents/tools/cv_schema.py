"""Profil maître (SPEC 5.1) et contenu d'un CV : types partagés par les agents de la phase 6 et
les features (le moteur n'importe aucune feature, contrat 6).

Chaque fait du profil porte un identifiant stable attribué par le code, jamais par le modèle
(`assign_fact_ids`) : préfixe par genre (`x` expérience, `x1a2` réalisation, `f` formation,
`f1d1` détail, `c` compétence, `p` projet, `p1a1` réalisation de projet, `l` langue, `k` lien,
`t` titre, `s` résumé) puis un numéro. Les modifications d'un CV citent ces identifiants.
"""

import re
from collections.abc import Iterable, Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

FactSource = Literal["cv", "linkedin", "note", "january"]
SectionKey = Literal[
    "summary", "experience", "education", "skills", "projects", "languages", "links"
]
ModificationAction = Literal["rewrite", "add", "remove", "move"]
ModificationType = Literal["keyword", "clarity", "impact", "order", "length", "title"]

_MONTH = r"^\d{4}(-(0[1-9]|1[0-2]))?$"  # « AAAA-MM » ou « AAAA »


def _sources() -> Any:
    """Le champ `sources` d'un fait : un `FieldInfo` neuf par classe, jamais partagé."""
    return Field(default_factory=list, max_length=4)


class Line(BaseModel):
    id: str = ""
    text: str = Field(min_length=1, max_length=600)


class Experience(BaseModel):
    id: str = ""
    role: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    start: str | None = Field(default=None, pattern=_MONTH)
    end: str | None = Field(default=None, pattern=_MONTH)
    achievements: list[Line] = Field(default_factory=list, max_length=15)
    sources: list[FactSource] = _sources()


class Education(BaseModel):
    id: str = ""
    degree: str = Field(min_length=1, max_length=160)
    school: str = Field(min_length=1, max_length=160)
    start: str | None = Field(default=None, pattern=_MONTH)
    end: str | None = Field(default=None, pattern=_MONTH)
    details: list[Line] = Field(default_factory=list, max_length=6)
    sources: list[FactSource] = _sources()


class SkillFact(BaseModel):
    id: str = ""
    name: str = Field(min_length=1, max_length=80)
    category: str | None = Field(default=None, max_length=60)
    sources: list[FactSource] = _sources()


class Project(BaseModel):
    id: str = ""
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    link: str | None = Field(default=None, max_length=300)
    achievements: list[Line] = Field(default_factory=list, max_length=8)
    sources: list[FactSource] = _sources()


class Language(BaseModel):
    id: str = ""
    name: str = Field(min_length=1, max_length=40)
    level: str | None = Field(default=None, max_length=40)
    sources: list[FactSource] = _sources()


class Link(BaseModel):
    id: str = ""
    label: str = Field(min_length=1, max_length=40)
    url: str = Field(max_length=300)
    sources: list[FactSource] = _sources()


class Identity(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    headline: str | None = Field(default=None, max_length=200)


class MasterProfileData(BaseModel):
    identity: Identity
    title: Line | None = None
    summary: Line | None = None
    experiences: list[Experience] = Field(default_factory=list, max_length=30)
    education: list[Education] = Field(default_factory=list, max_length=15)
    skills: list[SkillFact] = Field(default_factory=list, max_length=80)
    projects: list[Project] = Field(default_factory=list, max_length=20)
    languages: list[Language] = Field(default_factory=list, max_length=10)
    links: list[Link] = Field(default_factory=list, max_length=10)


class _HasId(Protocol):
    id: str


class _Sourced(Protocol):
    id: str
    sources: list[FactSource]


def _renumber(items: Sequence[_HasId], prefix: str) -> None:
    """Garde les ids `<prefix><n>` bien formés et uniques ; numérote les autres à la suite du
    plus grand numéro déjà pris (un doublon garde sa première occurrence)."""
    pattern = re.compile(rf"^{re.escape(prefix)}([1-9]\d*)$")
    taken: set[str] = set()
    top = 0
    fresh: list[_HasId] = []
    for item in items:
        match = pattern.match(item.id)
        if match is None or item.id in taken:
            fresh.append(item)
            continue
        taken.add(item.id)
        top = max(top, int(match.group(1)))
    for item in fresh:
        top += 1
        item.id = f"{prefix}{top}"


def assign_fact_ids(profile: MasterProfileData) -> MasterProfileData:
    """Une copie du profil où chaque fait a un identifiant stable (voir l'en-tête du module).
    Un id d'enfant (réalisation, détail) doit commencer par l'id de son parent."""
    out = profile.model_copy(deep=True)
    _renumber([line for line in (out.title,) if line is not None], "t")
    _renumber([line for line in (out.summary,) if line is not None], "s")
    _renumber(out.experiences, "x")
    for experience in out.experiences:
        _renumber(experience.achievements, f"{experience.id}a")
    _renumber(out.education, "f")
    for education in out.education:
        _renumber(education.details, f"{education.id}d")
    _renumber(out.skills, "c")
    _renumber(out.projects, "p")
    for project in out.projects:
        _renumber(project.achievements, f"{project.id}a")
    _renumber(out.languages, "l")
    _renumber(out.links, "k")
    return out


def _joined(*parts: str | None) -> str:
    return " — ".join(part for part in parts if part)


def _lines(lines: Iterable[Line]) -> dict[str, str]:
    return {line.id: line.text for line in lines}


def facts_of(profile: MasterProfileData) -> dict[str, str]:
    """id → texte lisible du fait (« Rôle — Entreprise », texte d'une réalisation…), dans
    l'ordre du profil. Les faits sans id (profil non numéroté) sont omis."""
    facts: dict[str, str] = {}
    for line in (profile.title, profile.summary):
        if line is not None:
            facts[line.id] = line.text
    for experience in profile.experiences:
        facts[experience.id] = _joined(experience.role, experience.company)
        facts.update(_lines(experience.achievements))
    for education in profile.education:
        facts[education.id] = _joined(education.degree, education.school)
        facts.update(_lines(education.details))
    facts.update({skill.id: skill.name for skill in profile.skills})
    for project in profile.projects:
        facts[project.id] = _joined(project.name, project.description)
        facts.update(_lines(project.achievements))
    facts.update({lang.id: _joined(lang.name, lang.level) for lang in profile.languages})
    facts.update({link.id: _joined(link.label, link.url) for link in profile.links})
    facts.pop("", None)
    return facts


def in_cv(profile: MasterProfileData) -> set[str]:
    """Les ids des faits venus du CV d'origine : ceux dont `sources` contient « cv », avec les
    réalisations et détails de leurs parents ; le titre et le résumé, sans sources, en font
    partie."""
    ids = {line.id for line in (profile.title, profile.summary) if line is not None}
    for experience in profile.experiences:
        if "cv" in experience.sources:
            ids |= {experience.id, *(line.id for line in experience.achievements)}
    for education in profile.education:
        if "cv" in education.sources:
            ids |= {education.id, *(line.id for line in education.details)}
    for project in profile.projects:
        if "cv" in project.sources:
            ids |= {project.id, *(line.id for line in project.achievements)}
    flat: list[_Sourced] = [*profile.skills, *profile.languages, *profile.links]
    ids |= {fact.id for fact in flat if "cv" in fact.sources}
    ids.discard("")
    return ids


class CvLine(BaseModel):
    """Une ligne d'un CV, adossée aux faits du profil qu'elle reformule."""

    text: str = Field(min_length=1, max_length=600)
    fact_ids: list[str] = Field(default_factory=list)


class CvEntry(BaseModel):
    heading: str = Field(default="", max_length=160)
    subheading: str | None = None
    dates: str | None = None
    lines: list[CvLine] = Field(default_factory=list)
    fact_id: str | None = None


class CvSection(BaseModel):
    key: SectionKey
    title: str = Field(min_length=1, max_length=60)
    entries: list[CvEntry] = Field(default_factory=list)
    items: list[CvLine] = Field(default_factory=list)


class CvContent(BaseModel):
    """Contenu d'un CV (gabarit rempli) : un ordre de sections, des lignes adossées à des faits."""

    name: str
    headline: str | None = None
    contact: list[str] = Field(default_factory=list)
    sections: list[CvSection] = Field(default_factory=list)
