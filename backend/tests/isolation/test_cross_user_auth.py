"""Routeur `auth` : deux comptes connectés ont chacun leur identité, la déconnexion de l'un ne
ferme pas la session de l'autre, et le cookie de l'un ne donne jamais l'identité de l'autre."""

from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.isolation.conftest import Browser

ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


async def test_two_accounts_have_their_own_identity(google_client_factory: Browser) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    mine = (await camille.get(ME)).json()
    theirs = (await dominique.get(ME)).json()
    assert (mine["email"], theirs["email"]) == (CAMILLE, DOMINIQUE)
    assert mine["id"] != theirs["id"]
    assert DOMINIQUE not in (await camille.get(ME)).text  # rien de l'autre dans sa réponse

    # Se déconnecter ne ferme que sa propre session.
    assert (await dominique.post(LOGOUT)).status_code == 204
    assert (await dominique.get(ME)).status_code == 401
    still = await camille.get(ME)
    assert still.status_code == 200 and still.json()["id"] == mine["id"]


async def test_a_cookie_never_gives_another_identity(google_client_factory: Browser) -> None:
    camille = await google_client_factory(CAMILLE)
    dominique = await google_client_factory(DOMINIQUE)
    token = camille.cookies.get("tremplin_session")
    assert token and token != dominique.cookies.get("tremplin_session")
    dominique.cookies.clear()
    # Contrôle positif : un témoin posé à la main (sans domaine, donc envoyé) est bien lu. Le
    # vrai témoin de Camille ouvre son compte à elle, jamais celui de Dominique.
    dominique.cookies.set("tremplin_session", token)
    sent = await dominique.get(ME)
    assert sent.status_code == 200 and sent.json()["email"] == CAMILLE
    # Un jeton inventé à partir du sien n'ouvre aucun compte.
    forged = token[:-1] + ("A" if token[-1] != "A" else "B")
    dominique.cookies.clear()
    dominique.cookies.set("tremplin_session", forged)
    refused = await dominique.get(ME)
    assert refused.status_code == 401 and refused.json()["error"]["code"] == "auth_required"
