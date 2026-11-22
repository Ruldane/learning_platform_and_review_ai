"""Un compte tiers ne peut lire, ouvrir ou remettre le Boss d'un programme."""

from fastapi import FastAPI

from tests.isolation.conftest import Browser
from tests.support.boss import completed_program


async def test_boss_belongs_to_its_program_owner(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("boss-a@example.test")
    other = await google_client_factory("boss-b@example.test")
    me = (await owner.get("/api/v1/auth/me")).json()["id"]
    route = f"/api/v1/boss/programs/{await completed_program(google_app, me)}"
    assert (await owner.post(route)).status_code == 201
    for method, suffix in (("GET", ""), ("POST", ""), ("POST", "/submit")):
        response = await other.request(method, route + suffix)
        assert response.status_code == 404
