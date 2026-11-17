"""Cas d'isolation du flux B : un test par routeur (lu par le test garde de 9.A4 après la
fusion ; ce module n'importe rien)."""

_COSTS = "tests/features/costs/test_router.py::test_other_user_calls_invisible"
_ACCOUNT = "tests/features/account/test_export.py::test_export_has_only_own_rows"

CASES: dict[str, str] = {
    "app.features.costs.router": _COSTS,
    "app.features.account.router": _ACCOUNT,
}
