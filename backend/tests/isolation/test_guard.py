"""Test garde de l'isolation (17.2, P14) : un routeur ajouté à `FEATURE_ROUTERS` sans test qui
prouve qu'un autre compte ne voit rien chez lui fait échouer la suite."""

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import APIRouter

from app.features.registry import FEATURE_ROUTERS
from tests.isolation.guard_support import (
    EXEMPT,
    EXPECTED_FROM_B,
    case_modules,
    check_function,
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


def test_phase10_routers_have_their_isolation_case() -> None:
    """10.I : les routeurs `ide` (flux A) et `mcp` (flux B) ont leur cas, plus aucune attente."""
    cases = load_cases()
    assert {"app.features.ide.router", "app.features.mcp.router"} <= cases.keys()


def test_every_case_points_to_an_existing_test() -> None:
    cases = load_cases()
    assert cases, "aucun cas chargé"
    for router, nodeid in cases.items():
        resolve_test(nodeid, router)  # lève si le test manque, est sans rapport ou ignoré
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
    for name in ("fake_cases", "fake_cases.cases_x", "fake_cases.cases_y"):
        monkeypatch.delitem(sys.modules, name, raising=False)  # retirés aussi à la fin du test
    monkeypatch.setattr(
        support, "case_modules", lambda: [f"fake_cases.{n}" for n in ("cases_x", "cases_y")]
    )
    importlib.invalidate_caches()
    try:
        with pytest.raises(ValueError, match="deux modules"):
            support.load_cases()
    finally:
        for name in ("fake_cases", "fake_cases.cases_x", "fake_cases.cases_y"):
            sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "nodeid", ["pas_un_test", "tests/absent.py::test_x", "tests/conftest.py::inconnu"]
)
def test_a_case_pointing_nowhere_is_refused(nodeid: str) -> None:
    with pytest.raises((ValueError, FileNotFoundError, AttributeError)):
        resolve_test(nodeid)


# --- Un cas factice ne contente pas le garde (revue 9.A4, I1) ---


def test_a_case_naming_a_test_of_another_zone_is_refused() -> None:
    with pytest.raises(ValueError, match="n'est pas un test de app.features.cv.router.profile"):
        resolve_test(
            "tests/test_app.py::test_unknown_route_uses_error_format",
            "app.features.cv.router.profile",
        )
    with pytest.raises(ValueError, match="n'est pas un test de"):  # une autre feature, aussi
        resolve_test(
            "tests/features/postings/test_router.py::test_other_user_posting_is_404",
            "app.features.cv.router.profile",
        )


def test_a_test_of_the_routers_own_zone_is_accepted() -> None:
    nodeid = "tests/features/postings/test_router.py::test_other_user_posting_is_404"
    assert callable(resolve_test(nodeid, "app.features.postings.router"))


def test_an_isolation_test_must_involve_a_second_user() -> None:
    def test_alone(client: object) -> None:
        assert client

    def test_two_accounts(act_as: object, client: object) -> None:
        act_as(client)  # type: ignore[operator]

    with pytest.raises(ValueError, match="second utilisateur"):
        check_function("test_alone", test_alone)
    check_function("test_two_accounts", test_two_accounts)


def test_a_skipped_or_xfailed_test_is_refused() -> None:
    @pytest.mark.skip(reason="exemple")
    def test_skipped_other_user() -> None: ...

    @pytest.mark.xfail
    def test_xfailed_other_user() -> None: ...

    def test_fine_other_user() -> None: ...

    for function in (test_skipped_other_user, test_xfailed_other_user):
        with pytest.raises(ValueError, match="ignoré"):
            check_function(function.__name__, function)
    check_function("test_fine_other_user", test_fine_other_user)
    # Une marque posée sur le module entier compte aussi (une seule marque ou une liste).
    for marks in (pytest.mark.skip, [pytest.mark.skipif(True, reason="x")]):
        with pytest.raises(ValueError, match="ignoré"):
            check_function(
                "test_fine_other_user", test_fine_other_user, SimpleNamespace(pytestmark=marks)
            )


def test_a_function_that_is_not_a_test_is_refused() -> None:
    with pytest.raises(TypeError):
        check_function("helper_other_user", lambda: None)
    with pytest.raises(TypeError):
        check_function("test_x", "pas appelable")
