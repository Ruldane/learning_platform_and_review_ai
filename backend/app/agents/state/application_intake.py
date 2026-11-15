"""État du parcours `application_intake` (D141). La fiche est en base seulement après la
confirmation de January : l'état garde la phrase (l'entrée), le brouillon lu, les alertes de
doublon, la réponse à la question et l'identifiant de la fiche créée."""

from typing import Any, TypedDict


class ApplicationIntakeState(TypedDict, total=False):
    text: str  # la phrase de January : jamais journalisée (17.2)
    today: str  # le jour de January (ISO 8601)
    language: str  # la langue de son interface
    draft: dict[str, Any]  # `IntakeDraft` en JSON
    alerts: list[dict[str, Any]]  # `AlertView` en JSON, la plus forte d'abord
    answer: dict[str, Any] | None  # réponse relue : `{choice, draft}` ; `None` : question reposée
    application_id: str  # la fiche créée (`create`, `distinct`) ou ouverte (`open`)
    summary: str
