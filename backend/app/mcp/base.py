"""Les déclarations MCP (phase 10, P11) : ce qu'une feature expose à Claude, par liste blanche.

Aucune route n'est exposée d'elle-même : chaque route de `FEATURE_ROUTERS` est soit **déclarée**
(`McpAction`, avec son niveau), soit **exclue avec un motif** (`FeatureMcp.excluded`) ; un garde de
test échoue sinon. Idem pour chaque graphe de `GRAPHS` (`McpGraph`).

Niveaux : 1 lecture ; 2 écriture réversible (historique et annulation, base seulement) ;
3 action qui ne s'annule pas (suppression, envoi, écriture au profil maître) : l'appel crée une
demande « À confirmer », rien ne se fait avant que January la confirme ; 4 jamais exposé
(`NEVER_EXPOSED_FEATURES`, et dans `settings` : clés, modèles par niveau, surcharges par agent,
secrets). Les autres réglages passent par l'action dédiée `settings_update_preferences` (niveau 2),
qui lit l'objet, ne change que les champs non sensibles listés et réécrit le tout : `PUT /settings`
brut reste exclu, car il porte aussi les modèles."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

Level = Literal[1, 2, 3]

# Niveau 4 : jamais exposé au MCP (connexion, compte et ses données, le MCP lui-même).
NEVER_EXPOSED_FEATURES = frozenset({"auth", "account", "mcp"})


@dataclass(frozen=True)
class PrecheckInput:
    """Ce que reçoit un contrôle préalable (niveau 3) : la requête telle qu'elle serait envoyée
    (méthode, chemin, paramètres, corps) et l'utilisatrice concernée."""

    user_id: str
    method: str
    path: str
    params: Mapping[str, Any]
    body: Any = None


@dataclass(frozen=True)
class Verdict:
    """Le résultat d'un contrôle préalable, gardé dans la demande « À confirmer » : `ok` faux =
    la demande dit pourquoi elle est déconseillée (`reasons`, textes neutres), jamais un blocage
    silencieux. January décide."""

    ok: bool
    reasons: tuple[str, ...] = ()
    summary: str | None = None


@dataclass(frozen=True)
class McpAction:
    """Une route exposée : `route` = `"POST /postings"` (méthode et chemin sans `/api/v1`) ;
    `name` = nom de l'outil ; `side_effects="external"` (vecteurs, fichiers, appel externe) force
    le niveau 3, l'annulation ne couvrant que la base (P14) ; `untrusted` = chemins des champs de
    la réponse qui viennent du web (rendus comme données) ; `precheck` = contrôle préalable d'une
    action de niveau 3 (ex. validateur d'honnêteté du profil)."""

    route: str
    level: Level
    name: str
    summary: str | None = None
    side_effects: Literal["db", "external"] = "db"
    untrusted: tuple[str, ...] = ()
    precheck: Callable[[PrecheckInput], Awaitable[Verdict]] | None = None


@dataclass(frozen=True)
class McpGraph:
    """Un graphe de l'application lancé par Claude (niveau 2) : les agents internes travaillent,
    Claude suit la session jusqu'au résultat."""

    graph: str
    level: Literal[2] = 2
    summary: str | None = None
    untrusted: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureMcp:
    """La déclaration d'une feature : ses actions, ses graphes, et ses routes exclues avec le motif
    (`"POST /ide/notes/{id}/accept" -> "geste réservé à l'interface"`)."""

    feature: str
    actions: tuple[McpAction, ...] = ()
    graphs: tuple[McpGraph, ...] = ()
    excluded: Mapping[str, str] = field(default_factory=dict)
