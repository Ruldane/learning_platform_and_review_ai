"""Radar des compétences par domaine et score de la courbe (SPEC F15, D99, D107) : règles pures.
Hors de `service` pour éviter un cycle avec `program` (voir 5.10)."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from math import floor

from app.db.models.skills import LEVEL_ORDER, SkillLevel

LEVEL_SCORE: dict[SkillLevel | None, int] = {
    None: 0,
    "declare": 25,
    "en_cours": 50,
    "valide": 75,
    "prouve": 100,
}
OTHER_DOMAIN = "Autres"


def as_level(value: str) -> SkillLevel:
    """Le niveau rangé en base ; une valeur inconnue se lit `declare`."""
    for level in LEVEL_ORDER:
        if level == value:
            return level
    return "declare"


def domain_name(domain: str | None) -> str:
    """Le domaine affiché : « Autres » pour une compétence sans domaine."""
    return (domain or "").strip() or OTHER_DOMAIN


def _rounded_mean(values: Sequence[int]) -> int:
    return floor(sum(values) / len(values) + 0.5) if values else 0


def domain_scores(rows: Sequence[tuple[str | None, SkillLevel | None]]) -> list[tuple[str, int]]:
    """La moyenne des scores de niveau par domaine (entier, 0,5 arrondi au-dessus), trié par
    nom ; une compétence sans domaine va dans « Autres »."""
    scores: dict[str, list[int]] = defaultdict(list)
    for domain, level in rows:
        scores[domain_name(domain)].append(LEVEL_SCORE[level])
    return [
        (name, _rounded_mean(values))
        for name, values in sorted(scores.items(), key=lambda item: item[0].casefold())
    ]


def mean_score(levels: Sequence[SkillLevel]) -> int:
    """Le score d'un relevé (courbe de progression, D107) : moyenne des scores de niveau des
    compétences qui ont un niveau, 0,5 arrondi au-dessus ; 0 sans compétence."""
    return _rounded_mean([LEVEL_SCORE[level] for level in levels])


def level_counts(levels: Iterable[SkillLevel]) -> dict[SkillLevel, int]:
    """Le nombre de compétences par niveau, les quatre niveaux toujours présents."""
    counts: dict[SkillLevel, int] = dict.fromkeys(LEVEL_ORDER, 0)
    for level in levels:
        counts[level] += 1
    return counts
