"""L'issue d'une évaluation (`ReviewOutcome`) passe d'un nœud au suivant dans l'état du parcours :
JSON en entrée de l'état, dataclass en sortie (P3). Les nombres de la phrase de fin sont comptés
ici, par le code."""

from typing import Any

from pydantic import TypeAdapter

from app.agents.tools.project_port import ReviewOutcome

_ADAPTER = TypeAdapter(ReviewOutcome)


def to_state(outcome: ReviewOutcome) -> dict[str, Any]:
    return dict(_ADAPTER.dump_python(outcome, mode="json"))


def from_state(data: dict[str, Any]) -> ReviewOutcome:
    return _ADAPTER.validate_python(data)


def _plural(number: int, one: str, many: str) -> str:
    return f"{number} {one if number < 2 else many}"


def summary_text(outcome: ReviewOutcome) -> str:
    """« Projet validé : 4 brouillons prêts, 1 à vérifier. » ou « Projet à reprendre : 2 critères
    sur 5 non atteints. » : des nombres comptés par le code, aucun texte du projet."""
    if outcome.verdict == "validated":
        drafts = outcome.drafts or []
        ready = sum(draft.status == "ready" for draft in drafts)
        text = f"Projet validé : {_plural(ready, 'brouillon prêt', 'brouillons prêts')}"
        return f"{text}, {len(drafts) - ready} à vérifier." if len(drafts) > ready else f"{text}."
    unmet = sum(not result.met for result in outcome.results)
    if unmet == 0:  # un résultat hors de l'énoncé a empêché la validation (`verdict`)
        return "Projet à reprendre : l'évaluation ne correspond pas à l'énoncé."
    total = len(outcome.results)
    many = unmet > 1
    return (
        f"Projet à reprendre : {unmet} {'critères' if many else 'critère'} sur {total} "
        f"{'non atteints' if many else 'non atteint'}."
    )
