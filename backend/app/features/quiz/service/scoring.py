"""Notes d'un quiz (SPEC F9, D99) : règles pures. Un QCM vaut 0 ou 1 point, une question
ouverte 0, 0,5 ou 1 selon la grille ; 80 % ou plus fait passer l'acquis à `valide`."""

from collections.abc import Sequence
from math import floor

from app.core.skills import normalize_skill_name

PASS_PERCENT = 80
OPEN_SCORES = (0.0, 0.5, 1.0)


def qcm_points(correct_index: int | None, choice: int | None) -> float:
    """1 point si January a choisi la bonne réponse, sinon 0 (sans réponse comprise)."""
    return 1.0 if correct_index is not None and choice == correct_index else 0.0


def score_percent(points: Sequence[float]) -> int:
    """Le score en pourcentage entier, arrondi à l'entier le plus proche (12,5 donne 13) ;
    aucune question : 0."""
    if not points:
        return 0
    return floor(100 * sum(points) / len(points) + 0.5)


def passed(score: int) -> bool:
    return score >= PASS_PERCENT


def weak_skills(skills: Sequence[str], points: Sequence[float], limit: int = 3) -> list[str]:
    """Les compétences des questions sous 1 point, dans l'ordre d'apparition, sans doublon
    (nom normalisé ; la première graphie est gardée), `limit` au plus."""
    weak: dict[str, str] = {}
    for name, point in zip(skills, points, strict=True):
        norm = normalize_skill_name(name)
        if point < 1 and norm and norm not in weak:
            weak[norm] = name.strip()
    return list(weak.values())[: max(0, limit)]
