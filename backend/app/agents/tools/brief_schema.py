"""Schémas du brief du jour (P11) : le choix de l'Éclaireur (une ressource parmi huit résultats) et
les deux phrases du conseil (Modérateur). Rien ici n'invente une donnée : la ressource vient d'un
résultat réel que le code a lu, les nombres du conseil sont contrôlés par le code
(`numbers_in_advice`) contre les faits du jour avant d'être rangés."""

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator

from app.agents.runtime.prose import Prose
from app.agents.tools.cv_lexicon import figures_in

RESULTS = 8  # résultats de la recherche du mois montrés à l'Éclaireur
READS = 3  # lectures de page au plus pour la ressource (choix, puis résultats suivants)
SENTENCES = 2  # phrases du conseil
SENTENCE_MIN = 10
SENTENCE_MAX = 240


class ResourcePick(BaseModel):
    """Le choix de l'Éclaireur : le rang (1 à 8) du résultat, `None` si aucun ne convient, et une
    phrase qui dit pourquoi."""

    index: int | None = Field(ge=1, le=RESULTS)
    why: Prose = Field(max_length=200)


class CouncilAdvice(BaseModel):
    """Le conseil du jour : exactement deux phrases de 10 à 240 caractères."""

    sentences: list[str] = Field(min_length=SENTENCES, max_length=SENTENCES)

    @field_validator("sentences")
    @classmethod
    def _sentence_lengths(cls, sentences: list[str]) -> list[str]:
        cleaned = [" ".join(sentence.split()) for sentence in sentences]
        if any(not SENTENCE_MIN <= len(sentence) <= SENTENCE_MAX for sentence in cleaned):
            raise ValueError(f"chaque phrase compte de {SENTENCE_MIN} à {SENTENCE_MAX} caractères")
        return cleaned


@dataclass(frozen=True)
class ResourceView:
    """La ressource du jour, telle que le port la range : un résultat réel dont la page a été
    lue. `published` : sa date si le web la donne, jamais devinée."""

    title: str
    url: str
    domain: str
    published: str | None
    why: str


def numbers_in_advice(sentences: Sequence[str]) -> set[str]:
    """Les nombres du conseil, sous forme canonique (`cv_lexicon`) : ceux en chiffres comme ceux
    écrits en lettres (« trois heures » est le nombre 3, pas une façon d'en citer un sans le
    dire). Le code les confronte aux faits du jour."""
    found: set[str] = set()
    for sentence in sentences:
        found |= figures_in(sentence)
    return found
