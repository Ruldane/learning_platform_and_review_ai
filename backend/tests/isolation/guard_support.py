"""Outils du test garde de l'isolation (17.2, P14) : chaque routeur de `FEATURE_ROUTERS` a un test
qui prouve qu'un autre compte ne lit ni n'écrit rien chez lui. Les cas sont écrits par flux, dans
`tests/isolation/cases_<flux>.py` ; ce module ne fait que les réunir."""

import importlib
from pathlib import Path

from fastapi import APIRouter

# Routeur → pourquoi il n'a pas de cas d'isolation.
EXEMPT: dict[str, str] = {"app.features.health.router": "aucune donnée d'utilisatrice"}

# Routeurs dont le cas vient du flux B (`cases_b.py`), absent de l'arbre du flux A. Le test garde
# les tolère **seulement** tant que `cases_b.py` n'existe pas ; dès que le flux B est fusionné, ce
# registre doit être vidé (`test_expected_from_b_is_emptied_once_b_delivers` échoue sinon) : un
# routeur oublié par B ne peut donc pas se cacher ici.
EXPECTED_FROM_B: frozenset[str] = frozenset(
    {"app.features.costs.router", "app.features.account.router"}
)

_HERE = Path(__file__).parent


def router_id(router: APIRouter) -> str:
    """Le module de l'endpoint de la première route du routeur (un paquet de routeurs, comme
    `memory` ou `cv`, se nomme par son premier sous-routeur : `app.features.cv.router.profile`)."""
    endpoint = _first_endpoint(router)
    if endpoint is None:
        raise ValueError("routeur sans aucune route")
    return str(endpoint.__module__)


def _first_endpoint(router: APIRouter) -> object | None:
    for route in router.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is not None:
            return endpoint
        included = getattr(route, "original_router", None)  # `include_router` : sous-routeur
        if included is not None and (found := _first_endpoint(included)) is not None:
            return found
    return None


def case_modules() -> list[str]:
    return sorted(f"tests.isolation.{p.stem}" for p in _HERE.glob("cases_*.py"))


def load_cases() -> dict[str, str]:
    """Fusion des `CASES` de tous les `cases_*.py` : routeur → identifiant de test
    (`tests/…/test_x.py::test_name`). Deux modules qui nomment le même routeur font échouer le
    chargement."""
    merged: dict[str, str] = {}
    for name in case_modules():
        cases: dict[str, str] = importlib.import_module(name).CASES
        for router, test in cases.items():
            if router in merged:
                raise ValueError(f"routeur {router} nommé par deux modules de cas ({name})")
            merged[router] = test
    return merged


def resolve_test(nodeid: str) -> object:
    """La fonction que désigne `tests/…/test_x.py::test_name` ; lève si le fichier, le module ou la
    fonction n'existe pas."""
    path, _, name = nodeid.partition("::")
    if not path.endswith(".py") or not name:
        raise ValueError(f"identifiant de test mal formé : {nodeid!r}")
    if not (_HERE.parent.parent / path).is_file():
        raise FileNotFoundError(path)
    module = importlib.import_module(path.removesuffix(".py").replace("/", "."))
    function = getattr(module, name)
    if not callable(function) or not name.startswith("test_"):
        raise TypeError(f"{nodeid} n'est pas un test")
    return function
