import httpx

API = "/api/v1/meeting-modules"


async def test_module_keeps_exact_excerpts_and_requires_explicit_publication(
    client: httpx.AsyncClient,
) -> None:
    body = {
        "title": "Réunion logistique",
        "transcript": (
            "Brief du vendredi.\n"
            "Nous avons décidé de garder le stock tampon à l’atelier.\n"
            "À étudier : Comparer les deux seuils de réapprovisionnement."
        ),
    }
    created = await client.post(API, json=body)
    assert created.status_code == 201, created.text
    draft = created.json()
    excerpts = {item["line"]: item for item in draft["excerpts"]}
    assert excerpts[2]["kind"] == "decision"
    assert excerpts[2]["text"] == "Nous avons décidé de garder le stock tampon à l’atelier."
    assert excerpts[3]["text"] in body["transcript"]
    path = f"{API}/{draft['id']}"
    assert (await client.post(f"{path}/publish", json={"lines": []})).status_code == 409
    selection = await client.put(f"{path}/selection", json={"lines": [2, 3]})
    assert selection.status_code == 200, selection.text
    assert selection.json()["status"] == "draft"
    assert len(selection.json()["steps"]) >= 2
    assert set(step["source_line"] for step in selection.json()["steps"]) == {2, 3}
    assert (await client.post(f"{path}/publish", json={"lines": [3]})).status_code == 409
    approved = {"lines": [2, 3]}
    published = await client.post(f"{path}/publish", json=approved)
    assert published.status_code == 200 and published.json()["status"] == "published"
    assert (await client.get(path)).json() == published.json()
    assert (await client.post(f"{path}/publish", json=approved)).json() == published.json()
    assert (await client.put(f"{path}/selection", json={"lines": [3]})).status_code == 409
