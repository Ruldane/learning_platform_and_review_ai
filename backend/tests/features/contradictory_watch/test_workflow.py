import httpx

API = "/api/v1/contradictory-watch"


async def test_experiment_freezes_two_sources_and_records_the_measurement(
    client: httpx.AsyncClient,
) -> None:
    study = {
        "title": "Comparer les temps de rendu",
        "sources": [
            {
                "url": "https://example.org/documentation",
                "version": "1.2",
                "claim": "Le rendu se termine en moins de 80 ms.",
            },
            {
                "url": "https://example.net/mesures",
                "version": "2026-11-20",
                "claim": "Le rendu dure au moins 100 ms.",
            },
        ],
        "protocol": "Charger le même fichier dix fois sur le même appareil à froid.",
        "criterion": "Comparer la médiane en millisecondes aux deux seuils.",
    }
    created = await client.post(API, json=study)
    assert created.status_code == 201, created.text
    expected = created.json()
    assert expected["status"] == "ready"
    path = f"{API}/{expected['id']}"
    assert (await client.get(path)).json() == expected
    observation = {"measurement": "92 ms", "outcome": "inconclusive"}
    closed = await client.post(f"{path}/observations", json=observation)
    assert closed.status_code == 200, closed.text
    assert closed.json()["sources"] == study["sources"]
    assert closed.json()["observation"] == observation
    assert (await client.post(f"{path}/observations", json=observation)).json() == closed.json()
    competing = {**observation, "outcome": "first"}
    assert (await client.post(f"{path}/observations", json=competing)).status_code == 409
