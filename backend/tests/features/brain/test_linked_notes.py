"""Les renvois Obsidian résolvent des éléments courants du même dossier."""

import httpx
from fastapi import FastAPI

from tests.features.brain.test_sync import API, BRAIN, SYNC, auth, configure, memory_items, upload


async def _note(
    client: httpx.AsyncClient,
    folder: dict[str, object],
    token: str,
    path: str,
    title: str,
    body: str = "Ce texte fictif représente le corps d'une note synchronisée.",
) -> None:
    wrote = await upload(client, folder, token, f"# {title}\n\n{body}\n".encode(), path)
    assert wrote.status_code == 202, wrote.text


async def test_wiki_links_resolve_by_title_and_path_without_guessing_ambiguous_notes(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    folder, token = await configure(client)
    elsewhere = await client.post(
        f"{BRAIN}/folders", json={"name": "Autre", "path": "C:/fictif/autre"}
    )
    assert elsewhere.status_code == 201
    await _note(client, elsewhere.json(), token, "autre.md", "Note d’un autre dossier")
    await _note(
        client,
        folder,
        token,
        "notes/origine.md",
        "Origine",
        (
            "Une note fictive qui cite [[Projet Alpha]], [[fiches/fiche-b|une fiche]], [[Sosie]], "
            "[[Note d’un autre dossier]], [[./absente]], [[Projet Alpha]]."
        ),
    )
    await _note(client, folder, token, "divers/acronyme.md", "Projet Alpha")
    await _note(client, folder, token, "fiches/fiche-b.md", "Fiche B")
    await _note(client, folder, token, "notes/sosie-1.md", "Sosie")
    await _note(client, folder, token, "notes/sosie-2.md", "Sosie")
    await app.state.memory.jobs.join()

    items = {item["title"]: item["id"] for item in await memory_items(client)}
    path = f"{API}/memory/items/{items['Origine']}"
    detail = await client.get(path)
    assert detail.status_code == 200, detail.text
    assert detail.json()["linked_notes"] == [
        {"item_id": items["Projet Alpha"], "title": "Projet Alpha"},
        {"item_id": items["Fiche B"], "title": "Fiche B"},
    ]

    removed = await client.post(
        f"{SYNC}/{folder['id']}/remove", headers=auth(token), json={"path": "fiches/fiche-b.md"}
    )
    assert removed.status_code == 204
    assert (await client.get(path)).json()["linked_notes"] == [
        {"item_id": items["Projet Alpha"], "title": "Projet Alpha"},
    ]


async def test_ordinary_memory_details_return_an_empty_link_list(client: httpx.AsyncClient) -> None:
    created = await client.post(
        f"{API}/memory/items",
        json={
            "kind": "acquis",
            "title": "Un acquis",
            "text": "Ce texte contient [[un renvoi fictif]].",
        },
    )
    assert created.status_code in (200, 201), created.text
    item = await client.get(f"{API}/memory/items/{created.json()['id']}")
    assert item.status_code == 200 and item.json()["linked_notes"] == []
