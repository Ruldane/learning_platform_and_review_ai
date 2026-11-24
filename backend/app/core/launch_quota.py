"""Le plafond de lancements de parcours par le MCP (phase 10, M11) : un parcours d'agents coûte
l'API de January, et Claude peut en lancer par des dizaines de routes. Le compte se fait **à la
source**, là où l'application démarre une session (`SessionRunner.start`), quand l'appel vient du
MCP : aucune route ne le contourne, déclarée ou non.

Compteur en mémoire, par utilisatrice, sur 24 h glissantes. Un redémarrage le remet à zéro (comme
les limites par minute du MCP, D204 : il ne donne pas plus de droit qu'un jeton valide n'en a).
`reserve` compte avant le démarrage, sans `await` entre le contrôle et l'inscription : des appels
simultanés ne passent jamais tous ; `release` rend la place d'un lancement refusé avant d'avoir
démarré."""

from collections import deque
from datetime import UTC, datetime, timedelta

from app.core.errors import AppError

GRAPH_LAUNCHES_PER_DAY = 30
_WINDOW = timedelta(days=1)


class LaunchQuota:
    def __init__(self, limit: int = GRAPH_LAUNCHES_PER_DAY) -> None:
        self.limit = limit
        self._launches: dict[str, deque[datetime]] = {}

    def reserve(self, user_id: str, now: datetime | None = None) -> datetime:
        """Compte un lancement de plus ; rend son instant (pour `release`). Au-delà du plafond :
        `mcp_graph_quota` (429), sans aucun contenu ; rien n'est compté."""
        moment = now or datetime.now(UTC)
        launches = self._launches.setdefault(user_id, deque())
        while launches and launches[0] <= moment - _WINDOW:
            launches.popleft()
        if len(launches) >= self.limit:
            raise AppError(
                "mcp_graph_quota",
                f"The limit of {self.limit} workflow launches in a rolling 24-hour period "
                "has been reached. Try again later or ask January to start it in the app.",
                429,
                {"limit": self.limit, "window": "day"},
            )
        launches.append(moment)
        return moment

    def release(self, user_id: str, moment: datetime) -> None:
        """Rend la place d'un lancement qui n'a pas démarré."""
        launches = self._launches.get(user_id)
        if launches is not None and moment in launches:
            launches.remove(moment)
