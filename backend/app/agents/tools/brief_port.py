"""Port du brief du jour (P11, D161). `app.agents` n'importe aucune feature (contrat 6) : il décrit
ici ce dont le parcours `daily_brief` a besoin ; la feature `brief` l'implémente (tâche 8.6).

Le brief est un instantané du jour : le bloc, les révisions, les relances, les offres et
l'avancement sont **calculés par le code** (feature `brief`) ; seules la ressource (l'Éclaireur) et
les deux phrases du conseil (le Modérateur) passent par un modèle. Les faits du jour, le sujet et
les textes rangés sont des données de l'utilisatrice ou du web (17.2, 17.4) : jamais journalisés.

- `context` : lecture seule ; les faits du jour, ce qui est déjà rangé (`resource_done`,
  `advice_done`) et les nombres que le conseil a le droit de citer (`allowed_numbers`, calculés par
  le code sur les faits).
- `save_resource` : la ressource du jour, `None` = rubrique vide (aucun sujet, aucune page lisible,
  recherche en panne). Idempotent : la première écriture gagne, un nœud rejoué ne change rien.
- `save_advice` : les deux phrases du conseil, `None` = conseil `failed` (un nombre inventé, ou
  aucune réponse valable), ou `unavailable` (`unavailable=True` : aucun modèle, faute de clé).
  Idempotent de même ; un conseil rangé `None` le reste toute la journée (jamais de nouvel
  essai)."""

from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

from app.agents.tools.brief_schema import ResourceView
from app.core.errors import AppError

# Les codes d'erreur de la fabrique de modèles quand aucun modèle ne peut être construit (aucune
# clé, clé illisible, fournisseur inconnu) : le conseil est alors « indisponible », pas « échoué ».
MODEL_UNAVAILABLE_CODES = frozenset(
    {"llm_key_missing", "llm_key_unreadable", "llm_provider_unknown"}
)


@dataclass(frozen=True)
class AdviceFacts:
    """Les faits du jour, tels que le code les a comptés. Le conseil ne dit rien d'autre."""

    block_title: str | None  # le bloc d'étude du jour (`None` : aucun bloc prévu)
    block_minutes: int
    cards_due: int  # fiches à réviser
    reminders_due: int  # relances de candidature à faire
    offers: int  # offres à regarder
    best_score: int | None  # meilleur score de quiz récent
    week_planned: int  # tâches prévues cette semaine
    week_done: int  # tâches faites cette semaine
    streak_days: int  # jours d'étude de suite


@dataclass(frozen=True)
class BriefContext:
    brief_id: str
    day: date
    language: Literal["fr", "en"]
    topic: str | None  # le sujet de la ressource (`None` : aucune recherche)
    facts: AdviceFacts
    resource_done: bool
    advice_done: bool
    allowed_numbers: frozenset[str]  # nombres permis dans le conseil (forme canonique)


class BriefStore(Protocol):
    async def context(self, user_id: str, brief_id: str) -> BriefContext: ...

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None: ...

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None: ...


def brief_unavailable() -> AppError:
    return AppError("brief_unavailable", "Le brief du jour n'est pas branché sur ce moteur.", 503)


class _NoBrief:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def context(self, user_id: str, brief_id: str) -> BriefContext:
        raise brief_unavailable()

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None:
        raise brief_unavailable()

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None:
        raise brief_unavailable()


NO_BRIEF: BriefStore = _NoBrief()
