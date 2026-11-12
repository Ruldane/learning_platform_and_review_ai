"""Lancer une session hors d'une requête HTTP (D82) : un port d'une feature (choix d'un parcours
qui lance la construction du programme) ou une tâche planifiée (leçons à J-7).

Le lanceur existe avant le moteur et lui est lié ensuite (`main._lifespan`, juste après
`agent_runtime`) : la composition des ports peut le recevoir sans cycle (les ports sont donnés
au moteur, le moteur au lanceur). Non lié, ou serveur qui s'arrête : 503 `engine_unavailable`.
"""

import logging
from typing import Any

from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError

logger = logging.getLogger(__name__)

ENGINE_UNAVAILABLE = "Le moteur d'agents n'est pas prêt."
_STOPPING_CODE = "server_stopping"


def engine_unavailable() -> AppError:
    return AppError("engine_unavailable", ENGINE_UNAVAILABLE, 503)


class SessionLauncher:
    def __init__(self) -> None:
        self._runner: SessionRunner | None = None

    @property
    def runner(self) -> SessionRunner | None:
        return self._runner

    def bind(self, runner: SessionRunner) -> None:
        self._runner = runner

    def unbind(self) -> None:
        """À l'arrêt, avant celui du moteur : plus aucune session lancée par ce chemin."""
        self._runner = None

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> str:
        """Comme `SessionRunner.start` (entrée validée, session `running`, tâche lancée) ; rend
        l'id de la session. Les erreurs du runner (parcours inconnu, entrée invalide) passent
        telles quelles, sauf l'arrêt du serveur, rendu comme un moteur indisponible."""
        runner = self._runner
        if runner is None:
            logger.warning("Session non lancée (utilisateur %s) : moteur non lié", user_id)
            raise engine_unavailable()
        try:
            return await runner.start(user_id, graph, input, subject_type, subject_id)
        except AppError as exc:
            if exc.code != _STOPPING_CODE:
                raise
            logger.warning("Session non lancée (utilisateur %s) : serveur en arrêt", user_id)
            raise engine_unavailable() from None
