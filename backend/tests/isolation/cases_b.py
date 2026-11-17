"""Cas d'isolation du flux B : un test par routeur (lu par le test garde de 9.A4 après la
fusion ; ce module n'importe rien).

`account` : un seul test fait intervenir deux comptes sur les deux routes à la fois. Il exporte
Camille puis Dominique (aucune ligne de l'autre), supprime Camille (lignes, fichiers, vecteurs et
fils du checkpointer de Dominique intacts) et vérifie que l'export de Dominique n'a pas changé."""

_COSTS = "tests/features/costs/test_router.py::test_other_user_calls_invisible"
_ACCOUNT = "tests/features/account/test_delete.py::test_delete_keeps_other_user"

CASES: dict[str, str] = {
    "app.features.costs.router": _COSTS,
    "app.features.account.router": _ACCOUNT,
}
