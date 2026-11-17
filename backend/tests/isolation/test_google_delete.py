"""9.I (revue 9.B5, M2) : en mode Google, après « Tout supprimer », le témoin de la session close ne
rouvre rien, et l'autre compte reste connecté."""

from app.features.account.schemas import DELETE_CONFIRMATION
from tests.isolation.conftest import Browser

P = "/api/v1"


async def test_old_cookie_is_refused_after_delete(google_client_factory: Browser) -> None:
    camille = await google_client_factory("camille@example.org")
    dominique = await google_client_factory("dominique@example.org")
    old_cookies = dict(camille.cookies)
    assert old_cookies and (await camille.get(f"{P}/auth/me")).status_code == 200

    r = await camille.post(f"{P}/account/delete", json={"confirm": DELETE_CONFIRMATION})
    assert r.status_code == 204

    camille.cookies.clear()
    for name, value in old_cookies.items():
        camille.cookies.set(name, value)
    assert (await camille.get(f"{P}/auth/me")).status_code == 401
    assert (await dominique.get(f"{P}/auth/me")).status_code == 200
