"""Port du kit de candidature (SPEC 6.4, F16, D142). `app.agents` n'importe aucune feature
(contrat 6) : il décrit ici ce dont le parcours `application_kit` a besoin ; la feature
`applications` l'implémente (`AgentKitStore`, tâche 7.6).

Le profil, l'offre, les pièces écrites et le dossier sont des données personnelles ou non fiables
(17.2, 17.4) : jamais journalisés, ni ici ni par l'implémentation.

- `context` : lecture seule ; 404 `application_not_found` si la fiche n'est pas à January.
- `save_piece` : **idempotent par `(fiche, pièce, session)`** : un nœud rejoué après un arrêt
  (SPEC 9.4) relit la ligne de sa session, n'en écrit pas une seconde ; une nouvelle session
  remplace le contenu de la pièce (sauf si January l'a modifiée : `keep`). Rend l'id de la pièce.
- `save_dossier` : `companies.dossier`, ses pages lues et sa date, idempotent par session.
"""

from typing import Any, Protocol

from app.agents.tools.kit_schema import CompanyDossier, KitContext, KitKind, KitStatus, SourceRef
from app.core.errors import AppError


class KitStore(Protocol):
    async def context(self, user_id: str, application_id: str) -> KitContext: ...

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str: ...

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None: ...


def kit_unavailable() -> AppError:
    return AppError("kit_unavailable", "Application kits are unavailable in this runtime.", 503)


class _NoKit:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def context(self, user_id: str, application_id: str) -> KitContext:
        raise kit_unavailable()

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str:
        raise kit_unavailable()

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None:
        raise kit_unavailable()


NO_KIT: KitStore = _NoKit()
