"""Règles pures du radar du marché (P5 à P9) : classement des compétences demandées, évolution,
alertes « absente de ton programme », score d'une offre, salaire gardé, enrichissement du
référentiel. Rien ici n'importe la base ; seul le score de match vient de `gap`."""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any

from app.core.skills import normalize_skill_name
from app.db.models.skills import SkillLevel
from app.features.gap.service.score import GapRow, match_score

MIN_RUN = 30
MAX_RUN = 50
MAX_READS = 60
MAX_CANDIDATES = 80
HIGH_MATCH = 70
ALERT_SHARE = 0.5
ALERT_MIN_POSTINGS = 10
ALERT_MAX = 5
ENRICH_SHARE = 0.3
ENRICH_MAX = 15

_DIGITS = re.compile(r"\d+")
_ACQUIRED: frozenset[str] = frozenset({"validated", "proven"})


@dataclass(frozen=True)
class SkillFreq:
    """Une compétence du classement : demandée par `count` offres analysées, soit `share`
    (arrondie à 0,01), au rang `rank` (les ex æquo partagent leur rang)."""

    skill: str
    norm: str
    count: int
    share: float
    rank: int


@dataclass(frozen=True)
class SkillTrend(SkillFreq):
    """Une ligne du classement avec son évolution depuis le relevé précédent : `delta_share` en
    points de pourcentage, `delta_rank` en rangs gagnés (positif) ou perdus ; `new` : absente
    du relevé précédent. Sans relevé précédent : deltas à `None`, `new` à faux."""

    delta_share: float | None
    delta_rank: int | None
    new: bool


@dataclass(frozen=True)
class Alert:
    """Une compétence très demandée et absente du programme (règle P8)."""

    skill: str
    share: float
    message: str


def _percent(count: int, total: int) -> int:
    """`count / total` en pour cent entier, arrondi au plus proche (,5 vers le haut), en entiers."""
    return (200 * count + total) // (2 * total)


def _skill_names(posting: Mapping[str, Any]) -> dict[str, str]:
    """Les compétences d'une offre : nom normalisé → nom tel qu'écrit (la première forme), une
    fois chacune."""
    names: dict[str, str] = {}
    for item in posting.get("skills") or []:
        name = str(item.get("name") or "").strip()
        norm = normalize_skill_name(name)
        if norm:
            names.setdefault(norm, name)
    return names


def rank_skills(postings: Sequence[Mapping[str, Any]]) -> list[SkillFreq]:
    """Le classement des compétences des offres lues (`read == "ok"`) et analysées (`skills` est
    une liste, même vide). Une compétence compte une fois par offre (nom normalisé) ; elle
    s'affiche sous sa forme la plus fréquente ; `share` = `count` / offres analysées, arrondie à
    0,01 ; tri par `count` décroissant puis nom normalisé ; rangs 1, 2, 2, 4 (ex æquo)."""
    analysed = [p for p in postings if p.get("read") == "ok" and isinstance(p.get("skills"), list)]
    counts: Counter[str] = Counter()
    forms: dict[str, Counter[str]] = {}
    for posting in analysed:
        names = _skill_names(posting)
        counts.update(names.keys())
        for norm, name in names.items():
            forms.setdefault(norm, Counter())[name] += 1
    ordered = sorted(counts, key=lambda norm: (-counts[norm], norm))
    out: list[SkillFreq] = []
    for position, norm in enumerate(ordered, start=1):
        rank = out[-1].rank if out and out[-1].count == counts[norm] else position
        display = min(forms[norm], key=lambda form: (-forms[norm][form], form))
        share = _percent(counts[norm], len(analysed)) / 100
        out.append(SkillFreq(display, norm, counts[norm], share, rank))
    return out


def evolution(
    current: Sequence[SkillFreq], previous: Sequence[SkillFreq] | None
) -> list[SkillTrend]:
    """Le classement `current` avec son évolution depuis `previous` (même poste, même zone), par
    nom normalisé : écart de part en points (entier), rang gagné (ancien − nouveau), `new` pour une
    compétence absente avant. Sans relevé précédent : tout à `None` et `new` faux."""
    before = None if previous is None else {item.norm: item for item in previous}
    trends: list[SkillTrend] = []
    for item in current:
        old = None if before is None else before.get(item.norm)
        points = None if old is None else round(item.share * 100) - round(old.share * 100)
        gained = None if old is None else old.rank - item.rank
        trends.append(
            SkillTrend(
                item.skill,
                item.norm,
                item.count,
                item.share,
                item.rank,
                delta_share=points,
                delta_rank=gained,
                new=before is not None and old is None,
            )
        )
    return trends


def alert_message(share: float) -> str:
    """Describe a skill that appears often in postings and is missing from the program."""
    return f"Requested in {round(share * 100)}% of postings and missing from your program."


def program_alerts(
    ranking: Sequence[SkillFreq],
    analyzed: int,
    in_program: AbstractSet[str],
    levels: Mapping[str, SkillLevel],
) -> list[Alert]:
    """Règle P8 : au moins `ALERT_MIN_POSTINGS` offres analysées ; une compétence demandée par au
    moins la moitié d'entre elles, absente de tout module non sauté (`in_program` : noms
    normalisés, synonymes du référentiel compris) et de niveau inférieur à `valide` (`levels` :
    par nom normalisé) ; `ALERT_MAX` au plus, dans l'ordre du classement."""
    if analyzed < ALERT_MIN_POSTINGS:
        return []
    alerts = [
        Alert(item.skill, item.share, alert_message(item.share))
        for item in ranking
        if item.share >= ALERT_SHARE
        and item.norm not in in_program
        and levels.get(item.norm) not in _ACQUIRED
    ]
    return alerts[:ALERT_MAX]


def posting_score(skills: Sequence[Mapping[str, Any]], levels: Mapping[str, SkillLevel]) -> int:
    """Le score de match d'une offre du radar (`match_score`, D118) : chaque compétence est une
    ligne `to_add` au niveau lu par nom normalisé, comptée une fois (requise si une des formes
    l'est). Aucune compétence : 0."""
    required: dict[str, bool] = {}
    names: dict[str, str] = {}
    for item in skills:
        name = str(item.get("name") or "").strip()
        norm = normalize_skill_name(name)
        if norm:
            names.setdefault(norm, name)
            required[norm] = required.get(norm, False) or bool(item.get("required"))
    rows = [GapRow(names[norm], required[norm], levels.get(norm), "to_add", None) for norm in names]
    return match_score(rows)


def salary_shown(salary: str | None, text: str) -> str | None:
    """Le salaire relevé par le modèle, gardé seulement si chacun de ses nombres figure dans le
    texte de l'offre (nombre entier de chiffres : 45 n'est pas 450). Un salaire sans aucun
    chiffre, vide ou absent : `None`."""
    figures = _DIGITS.findall(salary or "")
    if not figures:
        return None
    present = set(_DIGITS.findall(text))
    return (salary or "").strip() if all(figure in present for figure in figures) else None


def enrich_names(ranking: Sequence[SkillFreq]) -> list[str]:
    """Les compétences à ajouter au référentiel (F15) : demandées par au moins 30 % des offres,
    `ENRICH_MAX` au plus, dans l'ordre du classement."""
    return [item.skill for item in ranking if item.share >= ENRICH_SHARE][:ENRICH_MAX]


def low_sample(read_ok: int) -> bool:
    """Vrai si le relevé compte moins de `MIN_RUN` offres lisibles : le rapport le dit."""
    return read_ok < MIN_RUN
