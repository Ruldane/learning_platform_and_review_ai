"""Test garde de l'isolation (17.2, P14) : un routeur ajouté à `FEATURE_ROUTERS` sans test qui
prouve qu'un autre compte ne voit rien chez lui fait échouer la suite."""

import importlib
from pathlib import Path

import pytest
from fastapi import APIRouter

from app.features.registry import FEATURE_ROUTERS
from tests.isolation.guard_support import (
    EXEMPT,
    EXPECTED_FROM_B,
    case_modules,
    load_cases,
    resolve_test,
    router_id,
)

IDS = {router_id(r) for r in FEATURE_ROUTERS}


def test_every_router_has_isolation_case() -> None:
    missing = IDS - load_cases().keys() - EXEMPT.keys()
    assert missing - EXPECTED_FROM_B == set()


def test_expected_from_b_is_emptied_once_b_delivers() -> None:
    """`EXPECTED_FROM_B` ne couvre que l'absence de `cases_b.py` (arbre du flux A) : un routeur qui
    a son cas n'y figure plus, et plus rien n'y figure quand le flux B est fusionné."""
    assert EXPECTED_FROM_B <= IDS
    assert EXPECTED_FROM_B.isdisjoint(load_cases().keys())
    if "tests.isolation.cases_b" in case_modules():
        assert not EXPECTED_FROM_B


def test_every_case_points_to_an_existing_test() -> None:
    cases = load_cases()
    assert cases, "aucun cas chargé"
    for router, nodeid in cases.items():
        resolve_test(nodeid)  # lève si le fichier, le module ou la fonction manque
        assert router in IDS, f"{router} n'est plus un routeur de FEATURE_ROUTERS"


def test_exempt_routers_are_real_routers_with_a_reason() -> None:
    assert set(EXEMPT) <= IDS
    assert all(reason.strip() for reason in EXEMPT.values())
    assert not set(EXEMPT) & load_cases().keys()  # exempté ET couvert : l'un des deux est faux


def test_router_id_names_the_first_endpoint_module_even_through_include_router() -> None:
    assert "app.features.cv.router.profile" in IDS
    assert "app.features.memory.router.items" in IDS
    assert "app.features.health.router" in IDS
    assert len(IDS) == len(FEATURE_ROUTERS)  # deux routeurs ne partagent jamais un identifiant
    with pytest.raises(ValueError):
        router_id(APIRouter())


def test_two_case_modules_naming_the_same_router_fail_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tests.isolation.guard_support as support

    pkg = tmp_path / "fake_cases"
    pkg.mkdir()
    for name in ("cases_x", "cases_y"):
        (pkg / f"{name}.py").write_text('CASES = {"app.features.x.router": "a.py::test_a"}\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        support, "case_modules", lambda: [f"fake_cases.{n}" for n in ("cases_x", "cases_y")]
    )
    importlib.invalidate_caches()
    with pytest.raises(ValueError, match="deux modules"):
        support.load_cases()


@pytest.mark.parametrize(
    "nodeid", ["pas_un_test", "tests/absent.py::test_x", "tests/conftest.py::inconnu"]
)
def test_a_case_pointing_nowhere_is_refused(nodeid: str) -> None:
    with pytest.raises((ValueError, FileNotFoundError, AttributeError)):
        resolve_test(nodeid)
