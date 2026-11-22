"""Les déclarations MCP (phase 10, P11) : ce qu'une feature expose à Claude, par liste blanche.

Aucune route n'est exposée d'elle-même : chaque route de `FEATURE_ROUTERS` est soit **déclarée**
(`McpAction`, avec son niveau), soit **exclue avec un motif** (`FeatureMcp.excluded`) ; un garde de
test échoue sinon. Idem pour chaque graphe de `GRAPHS` (`McpGraph`).

Niveaux : 1 lecture ; 2 écriture réversible (historique et annulation, base seulement) ;
3 action qui ne s'annule pas (suppression, envoi, écriture au profil maître) : l'appel crée une
demande « À confirmer », rien ne se fait avant que January la confirme ; 4 jamais exposé
(`NEVER_EXPOSED_FEATURES`, et dans `settings` : clés, modèles par niveau, surcharges par agent,
secrets). Les autres réglages passent par l'action dédiée `settings_update_preferences` (niveau 2),
qui lit l'objet (`merge_from`), ne change que les champs non sensibles listés (`body_fields`) et
réécrit le tout : `PUT /settings` brut reste exclu, car il porte aussi les modèles. Une route
déclarée avec `body_fields` est permise même si sa feature a des champs sensibles (D1)."""

import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

Level = Literal[1, 2, 3]

# Niveau 4 : jamais exposé au MCP (connexion, compte et ses données, le MCP lui-même).
NEVER_EXPOSED_FEATURES = frozenset({"auth", "account", "mcp"})

# Des POST qui ne font que lire (recherche) : seuls à pouvoir être de niveau 1 sans être un GET,
# sinon un jeton en lecture seule ne pourrait pas chercher dans la mémoire.
READ_ONLY_POSTS = frozenset({"POST /memory/search"})


# Grammaire des chemins `untrusted` : chemins pointés dans `data` de la réponse JSON (la racine est
# `data`) ; `[]` = « chaque élément d'une liste » ; une réponse dont la racine est une liste se note
# `[].champ`. Exemples : `"description"`, `"items[].description"`, `"postings[].company"`,
# `"[].title"`, `"[].company.name"`. Ni `*`, ni indice, ni chemin vide.
_UNTRUSTED_PATH = re.compile(r"(\[\]\.)?[a-z_][a-z0-9_]*(\[\])?(\.[a-z_][a-z0-9_]*(\[\])?)*")


def untrusted_paths_valid(paths: tuple[str, ...]) -> bool:
    """Tous les chemins suivent la grammaire ci-dessus (vrai pour aucun chemin). L'enveloppement
    des champs (clôture « donnée non fiable ») est le travail du serveur MCP (B2)."""
    return all(_UNTRUSTED_PATH.fullmatch(path) for path in paths)


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
    la réponse qui viennent du web (rendus comme données ; grammaire : `untrusted_paths_valid`) ;
    `precheck` = contrôle préalable d'une action de niveau 3 (ex. validateur d'honnêteté du
    profil) ; `body_fields` (si non `None`) = liste blanche des champs du corps que le MCP peut
    envoyer, tout autre champ est refusé ; `merge_from` = route GET dont la réponse sert de base :
    l'adaptateur la lit, remplace seulement `body_fields` et renvoie le tout (exige `body_fields`).
    Un effet `external` est de niveau 3 au moins (`ValueError` sinon). `response_fields` (si non
    `None`) : l'adaptateur ne renvoie que ces clés de l'objet racine de la réponse (de chaque objet
    si c'est une liste), ex. les préférences sans les modèles ; `encoding="form"` : les champs
    texte du corps partent en `multipart/form-data` (aucun fichier), pour un formulaire.
    `launches` : le nom du graphe que la route lance (un parcours de `ROUTE_ONLY`) ; l'appel compte
    dans le plafond de lancements de graphes par jour (M11)."""

    route: str
    level: Level
    name: str
    summary: str | None = None
    side_effects: Literal["db", "external"] = "db"
    untrusted: tuple[str, ...] = ()
    precheck: Callable[[PrecheckInput], Awaitable[Verdict]] | None = None
    body_fields: frozenset[str] | None = None
    merge_from: str | None = None
    response_fields: frozenset[str] | None = None
    encoding: Literal["json", "form"] = "json"
    launches: str | None = None

    def __post_init__(self) -> None:
        if self.side_effects == "external" and self.level == 2:
            raise ValueError("un effet externe est de niveau 3 (P14)")
        if self.merge_from is not None and (
            self.body_fields is None or not self.merge_from.startswith("GET ")
        ):
            raise ValueError("merge_from est une route GET et exige body_fields")
        if not untrusted_paths_valid(self.untrusted):
            raise ValueError("chemin untrusted hors grammaire")


@dataclass(frozen=True)
class McpGraph:
    """Un graphe de l'application lancé par Claude (niveau 2) : les agents internes travaillent,
    Claude suit la session jusqu'au résultat."""

    graph: str
    level: Literal[2] = 2
    summary: str | None = None
    untrusted: tuple[str, ...] = ()
    # Un parcours qui n'a que sa route de lancement (`ROUTE_ONLY`) : pas d'outil `graph_<nom>` (il
    # serait refusé en 409), la déclaration ne sert qu'à rendre non fiables les champs du résultat
    # de la session quand Claude la suit.
    follow_only: bool = False
    # Le parcours n'a pas d'outil payant. Son nom graph_<nom> sert à agents_play_start.
    play_only: bool = False

    def __post_init__(self) -> None:
        if not untrusted_paths_valid(self.untrusted):
            raise ValueError("chemin untrusted hors grammaire")


@dataclass(frozen=True)
class FeatureMcp:
    """La déclaration d'une feature : ses actions, ses graphes, et ses routes exclues avec le motif
    (`"POST /ide/notes/{note_id}/accept" -> "geste réservé à l'interface"`, chemins réels) ; un
    graphe exclu a pour clé `"graph:<nom>"` (`"graph:cv_review" -> motif`)."""

    feature: str
    actions: tuple[McpAction, ...] = ()
    graphs: tuple[McpGraph, ...] = ()
    excluded: Mapping[str, str] = field(default_factory=dict)
    # Ces routes ne peuvent être appelées que sous le contexte de modèle joué.
    play_actions: tuple[McpAction, ...] = ()
