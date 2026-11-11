"""Réglages de l'utilisatrice dont le moteur a besoin pour une exécution.

Le moteur ne lit pas la feature `settings` (contrat d'import : `app.agents` n'importe jamais
`app.features`) : la composition (`app.bootstrap`) lui fournit une `RunSettingsSource`, adaptée
du service des réglages, comme la fabrique de modèles et la table des prix.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RunSettings:
    session_token_cap: int  # plafond de tokens par session (SPEC 9.3, 11.4)
    debate_rounds: int
    lesson_language: str
    search_languages: tuple[str, ...]
    style_guide: str


class RunSettingsSource(Protocol):
    async def get_run_settings(self, user_id: str) -> RunSettings: ...
