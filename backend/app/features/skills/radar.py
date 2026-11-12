"""Radar des compétences par domaine (SPEC F15, D99) : règles pures. Hors de `service` pour
éviter un cycle avec `program` (voir 5.10)."""

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


def domain_scores(rows: Sequence[tuple[str | None, SkillLevel | None]]) -> list[tuple[str, int]]:
    """La moyenne des scores de niveau par domaine (entier, 0,5 arrondi au-dessus), trié par
    nom ; une compétence sans domaine va dans « Autres »."""
    scores: dict[str, list[int]] = defaultdict(list)
    for domain, level in rows:
        scores[(domain or "").strip() or OTHER_DOMAIN].append(LEVEL_SCORE[level])
    return [
        (name, floor(sum(values) / len(values) + 0.5))
        for name, values in sorted(scores.items(), key=lambda item: item[0].casefold())
    ]


def level_counts(levels: Iterable[SkillLevel]) -> dict[SkillLevel, int]:
    """Le nombre de compétences par niveau, les quatre niveaux toujours présents."""
    counts: dict[SkillLevel, int] = dict.fromkeys(LEVEL_ORDER, 0)
    for level in levels:
        counts[level] += 1
    return counts
