"""État du parcours `application_kit` (D142). La fiche, son offre et le profil sont en base (port
`KitStore`) : chaque nœud relit le contexte par `context` (lecture seule) ; l'état ne garde que
l'identifiant de la fiche, les pièces gardées (modifiées par January, jamais refaites) et l'issue de
chaque pièce, que les branches parallèles écrivent sans se gêner (`outcomes`, fusion des dicts)."""

import operator
from typing import Annotated, TypedDict


class ApplicationKitState(TypedDict, total=False):
    application_id: str
    keep: list[str]  # pièces de `KitContext.keep`, non régénérées
    outcomes: Annotated[dict[str, str], operator.or_]  # pièce → statut rangé
    summary: str
