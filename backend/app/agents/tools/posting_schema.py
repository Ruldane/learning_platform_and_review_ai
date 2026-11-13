"""Analyse d'une offre d'emploi (SPEC 5.3 étape 1, F8) : sortie structurée de l'Analyste, lue
aussi par l'écart, la revue de CV et ses indicateurs. Le moteur n'importe aucune feature
(contrat 6) : ces types et la normalisation des termes vivent donc ici.

`normalize_term` est la seule normalisation des termes de la phase 6 (preflight G32) : mots clés
présents dans l'offre, couverture des exigences, présence des mots clés dans le CV, termes
d'outil du validateur. Les features l'importent d'ici.
"""

import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose

# Tout ce qui n'est ni lettre, ni chiffre, ni « + », ni « # » (C++, C#) sépare deux mots.
_SEPARATORS = re.compile(r"[^\w+#]|_")
_MIN_PLURAL_WORD = 4  # « s » final retiré des mots de 4 lettres au moins (« aws » reste)

Short = Annotated[str, Field(min_length=1, max_length=80)]


def normalize_term(text: str, *, plural: bool = False) -> str:
    """Le texte sans casse (`casefold`) ni accents, ponctuation changée en espaces, mots séparés
    d'une espace. `plural` retire en plus le « s » final d'un mot (pluriel simple)."""
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
    """`term` figure dans `text`, mots entiers, après `normalize_term` des deux côtés. Un terme
    vide après normalisation ne figure jamais."""
    needle = normalize_term(term, plural=plural)
    return bool(needle) and f" {needle} " in f" {normalize_term(text, plural=plural)} "


class Requirement(BaseModel):
    """Une exigence de l'offre ; `skills` : les compétences qu'elle demande, nommées."""

    text: Prose = Field(min_length=3, max_length=300)
    required: bool
    skills: list[Short] = Field(default_factory=list, max_length=6)


class Keyword(BaseModel):
    """Un mot clé de l'offre, dans sa formulation exacte (`term`) ; `variants` : ses autres
    formes (sigle, forme longue)."""

    term: str = Field(min_length=2, max_length=80)
    variants: list[Short] = Field(default_factory=list, max_length=5)


class Eliminatory(BaseModel):
    """Un critère éliminatoire (années d'expérience, lieu, langue, diplôme…)."""

    kind: Literal["experience_years", "location", "language", "degree", "other"]
    text: Prose = Field(min_length=3, max_length=200)


class SkillNeed(BaseModel):
    """Une compétence demandée ; `learnable` faux : hors du champ d'un programme (permis, langue
    maternelle…), elle part en « hors périmètre » dans l'écart."""

    name: str = Field(min_length=2, max_length=80)
    required: bool
    domain: str | None = Field(default=None, max_length=60)
    learnable: bool = True


class PostingAnalysis(BaseModel):
    is_job_posting: bool
    title: str = Field(min_length=2, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    level: Literal["junior", "confirme", "senior", "lead", "inconnu"]
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
    """Une phrase française, rendue au modèle, par mot clé qui ne figure pas tel quel dans le
    texte de l'offre (casse, accents, espaces et ponctuation ignorés ; mots entiers)."""
    return [
        f"Le mot clé « {keyword.term} » ne figure pas tel quel dans l'offre : "
        "recopie-le exactement comme il est écrit, ou retire-le."
        for keyword in analysis.keywords
        if not contains_term(text, keyword.term)
    ]


def requirement_problems(analysis: PostingAnalysis) -> list[str]:
    """Une phrase française, rendue au modèle, par exigence obligatoire qui ne nomme aucune
    compétence : sans compétence, elle ne serait jamais couverte (revue 6.2, m3)."""
    return [
        f"L'exigence obligatoire « {' '.join(requirement.text.split())[:80]} » ne nomme aucune "
        "compétence : ajoute dans `skills` au moins une compétence qu'elle demande."
        for requirement in analysis.requirements
        if requirement.required and not requirement.skills
    ]
