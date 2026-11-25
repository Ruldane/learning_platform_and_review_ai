"""Port du comité de recrutement simulé (SPEC F19, D147). `app.agents` n'importe aucune feature
(contrat 6) : il décrit ici ce dont le parcours `hiring_committee` a besoin ; la feature
`applications` l'implémente (`AgentCommitteeStore`, tâche 7.10).

Le CV, l'offre, le dossier, les paroles des personas et le profil sont des données personnelles ou
non fiables (17.2, 17.4) : jamais journalisés, ni ici ni par l'implémentation.

- `context` : lecture seule ; 404 `committee_not_found` si l'exécution n'est pas à January.
- `save_result` : **idempotent par session** : un nœud rejoué après un arrêt (SPEC 9.4) relit
  l'issue de sa session, n'écrit ni second vote, ni seconde synthèse, ni second événement. Range
  les quatre votes, le verdict, les objections classées et les trois changements, passe
  l'exécution à `done` et, si l'offre a une fiche, ajoute l'événement `committee` à son fil."""

from typing import Protocol

from app.agents.tools.committee_schema import CommitteeContext, PersonaVote, Synthesis
from app.core.errors import AppError


class CommitteeStore(Protocol):
    async def context(self, user_id: str, run_id: str) -> CommitteeContext: ...

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None: ...


def committee_unavailable() -> AppError:
    return AppError(
        "committee_unavailable", "The hiring committee is unavailable in this runtime.", 503
    )


class _NoCommittee:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def context(self, user_id: str, run_id: str) -> CommitteeContext:
        raise committee_unavailable()

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None:
        raise committee_unavailable()


NO_COMMITTEE: CommitteeStore = _NoCommittee()
