"""Même la topologie des notes synchronisées est isolée par compte."""

from fastapi import FastAPI

from tests.features.brain.test_linked_notes import _note
from tests.features.brain.test_sync import API, configure
from tests.isolation.conftest import Browser


async def test_galaxy_never_reads_another_accounts_nodes(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("galaxie-a@example.test")
    other = await google_client_factory("galaxie-b@example.test")
    assert (await owner.post(f"{API}/skills", json={"name": "Python fictif"})).status_code == 201
    assert (await other.post(f"{API}/skills", json={"name": "Jardinage fictif"})).status_code == 201
    folder, token = await configure(owner)
    await _note(owner, folder, token, "a.md", "Alpha", "Renvoi fictif [[Bêta]].")
    await _note(owner, folder, token, "b.md", "Bêta")
    await google_app.state.memory.jobs.join()
    mine = (await owner.get(f"{API}/galaxy")).json()
    theirs = (await other.get(f"{API}/galaxy")).json()
    assert {node["title"] for node in mine["nodes"]} == {"Python fictif", "Alpha", "Bêta"}
    assert [edge["kind"] for edge in mine["edges"]] == ["reference"]
    assert [node["title"] for node in theirs["nodes"]] == ["Jardinage fictif"]
    assert theirs["edges"] == []
