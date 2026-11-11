import httpx

from app.providers.llm.model_defaults import GLM_VISION


async def test_get_returns_defaults_with_computed_fields(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/settings")
    body = r.json()
    assert r.status_code == 200
    assert body["availability"]["weekly_budget_minutes"] == 840
    assert body["vision_enabled"] is True
    assert body["debate_rounds"] == 3 and body["tiers"]["vision"]["provider"] == "anthropic"


async def test_put_then_get_roundtrip(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json() | {"debate_rounds": 5, "style_guide": "ok"}
    r = await client.put("/api/v1/settings", json=body)
    assert r.status_code == 200 and r.json()["debate_rounds"] == 5
    again = (await client.get("/api/v1/settings")).json()
    assert again["debate_rounds"] == 5 and again["style_guide"] == "ok"


async def test_put_rejects_six_rounds(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json() | {"debate_rounds": 6}
    r = await client.put("/api/v1/settings", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


async def test_put_rejects_bad_hour(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json() | {"brief_time": "7h"}
    r = await client.put("/api/v1/settings", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


async def test_vision_disabled_when_tier_has_no_vision(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json()
    body["tiers"]["vision"] = {"provider": "glm", "model": "glm-4.7-flash"}
    assert (await client.put("/api/v1/settings", json=body)).json()["vision_enabled"] is False
    body["tiers"]["vision"] = {"provider": "glm", "model": GLM_VISION}
    assert (await client.put("/api/v1/settings", json=body)).json()["vision_enabled"] is True


async def test_put_accepts_a_get_response_and_ignores_extra_fields(
    client: httpx.AsyncClient,
) -> None:
    # Le corps d'un GET contient des champs calculés (vision_enabled, budget) et un champ inconnu
    # ne doit pas casser le PUT ni ressortir.
    body = (await client.get("/api/v1/settings")).json() | {"champ_inconnu": 1}
    r = await client.put("/api/v1/settings", json=body)
    assert r.status_code == 200 and "champ_inconnu" not in r.json()
    assert r.json()["availability"]["weekly_budget_minutes"] == 840


async def test_put_rejects_empty_model_or_provider_without_echo(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json()
    body["tiers"]["rapide"] = {"provider": "glm", "model": ""}
    body["agent_overrides"] = {"coach": {"provider": "", "model": "MODELE-ECHO-XYZ"}}
    r = await client.put("/api/v1/settings", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    locs = [err["loc"] for err in r.json()["error"]["details"]["errors"]]
    assert ["body", "tiers", "rapide", "model"] in locs
    assert ["body", "agent_overrides", "coach", "provider"] in locs
    assert "MODELE-ECHO-XYZ" not in r.text
