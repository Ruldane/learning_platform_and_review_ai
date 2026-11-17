"""Outils du test garde de l'isolation (17.2, P14) : chaque routeur de `FEATURE_ROUTERS` a un test
qui prouve qu'un autre compte ne lit ni n'écrit rien chez lui. Les cas sont écrits par flux, dans
`tests/isolation/cases_<flux>.py` ; ce module ne fait que les réunir."""

import importlib
import inspect
import re
from pathlib import Path

from fastapi import APIRouter

# Routeur → pourquoi il n'a pas de cas d'isolation.
EXEMPT: dict[str, str] = {"app.features.health.router": "aucune donnée d'utilisatrice"}

# Routeurs dont le cas devait venir du flux B : vidé en 9.I, `cases_b.py` est fusionné
# (`test_expected_from_b_is_emptied_once_b_delivers` échoue s'il ne l'est pas).
EXPECTED_FROM_B: frozenset[str] = frozenset()

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


# Un test d'isolation fait intervenir un second utilisateur : `act_as` (mode local), la fabrique de
# navigateurs du mode Google, ou un nom qui l'annonce (`OTHER`, `autre`, `second`, `DOMINIQUE`).
# Contrôle textuel volontairement simple : il écarte un test sans rapport (`test_health_ok`), pas
# une personne de mauvaise foi, que la revue de code rattrape.
SECOND_USER = re.compile(
    r"act_as|google_client_factory|other|autre|second|dominique", re.IGNORECASE
)
_SKIP_MARKS = frozenset({"skip", "skipif", "xfail"})


def _marks(obj: object) -> list[object]:
    """Les marques `pytest.mark` d'une fonction ou d'un module (une seule marque ou une liste)."""
    found = getattr(obj, "pytestmark", [])
    return list(found) if isinstance(found, list | tuple) else [found]


def check_path(router: str, path: str) -> None:
    """Le test cité vit sous `tests/isolation/` ou sous `tests/features/<zone>/`, `<zone>` étant la
    feature du routeur (`app.features.<zone>.…`) : un cas ne peut pas nommer un test d'ailleurs.
    Le routeur `mcp` a aussi `tests/mcp/` (le moteur du MCP et sa feature se testent ensemble)."""
    parts = router.split(".")
    zone = parts[2] if parts[:2] == ["app", "features"] and len(parts) > 2 else None
    allowed = ["tests/isolation/"] + ([f"tests/features/{zone}/"] if zone else [])
    if zone == "mcp":
        allowed.append("tests/mcp/")
    if not any(path.startswith(prefix) for prefix in allowed):
        raise ValueError(
            f"{path} n'est pas un test de {router} (attendu sous {' ou '.join(allowed)})"
        )


def check_function(name: str, function: object, module: object = None) -> None:
    """Un vrai test d'isolation : une fonction `test_*`, ni ignorée (`skip`, `skipif`, `xfail`, sur
    la fonction ou sur le module), qui fait intervenir un second utilisateur (`SECOND_USER`)."""
    if not callable(function) or not name.startswith("test_"):
        raise TypeError(f"{name} n'est pas un test")
    marks = [*_marks(function), *_marks(module)]
    if any(getattr(mark, "name", "") in _SKIP_MARKS for mark in marks):
        raise ValueError(f"{name} est ignoré (skip ou xfail) : il ne prouve rien")
    if not SECOND_USER.search(inspect.getsource(function)):
        raise ValueError(f"{name} ne fait intervenir aucun second utilisateur")


def resolve_test(nodeid: str, router: str | None = None) -> object:
    """La fonction que désigne `tests/…/test_x.py::test_name` ; lève si le fichier, le module ou la
    fonction n'existe pas. Avec `router`, vérifie aussi que le test le concerne (`check_path`) et
    qu'il prouve quelque chose (`check_function`)."""
    path, _, name = nodeid.partition("::")
    if not path.endswith(".py") or not name:
        raise ValueError(f"identifiant de test mal formé : {nodeid!r}")
    if router is not None:
        check_path(router, path)
    if not (_HERE.parent.parent / path).is_file():
        raise FileNotFoundError(path)
    module = importlib.import_module(path.removesuffix(".py").replace("/", "."))
    function = getattr(module, name)
    if router is None:
        if not callable(function) or not name.startswith("test_"):
            raise TypeError(f"{nodeid} n'est pas un test")
    else:
        check_function(name, function, module)
    return function
