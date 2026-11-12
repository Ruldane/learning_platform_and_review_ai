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


async def test_settings_defaults_include_starting_domain_lists(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json()
    assert body["preferred_domains"] == [
        "wikipedia.org",
        "arxiv.org",
        "github.com",
        "docs.python.org",
        "developer.mozilla.org",
        "pytorch.org",
        "huggingface.co",
        "scikit-learn.org",
    ]
    assert body["excluded_domains"] == [
        "pinterest.com",
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "linkedin.com",
    ]
    assert body["search_provider_order"] == ["searxng", "brave"]
    assert (body["search_max_queries"], body["search_max_pages"]) == (12, 30)
    assert body["search_languages"] == ["fr", "en"]


async def test_settings_rejects_unknown_provider_and_bad_domain(
    client: httpx.AsyncClient,
) -> None:
    base = (await client.get("/api/v1/settings")).json()
    for change in (
        {"search_provider_order": ["moteur-ECHO-XYZ"]},
        {"preferred_domains": ["pas un domaine ECHO-XYZ"]},
        {"excluded_domains": ["https://10.0.0.1/ECHO-XYZ"]},
    ):
        r = await client.put("/api/v1/settings", json=base | change)
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
        assert "ECHO-XYZ" not in r.text


async def test_settings_search_bounds(client: httpx.AsyncClient) -> None:
    base = (await client.get("/api/v1/settings")).json()
    for change in (
        {"search_provider_order": []},
        {"search_provider_order": ["brave", "brave"]},
        {"search_languages": []},
        {"search_languages": ["fr", "fr"]},
        {"search_languages": ["FR"]},
        {"search_languages": ["fr", "en", "es", "de", "it", "pt", "nl"]},
        {"preferred_domains": [f"d{i}.org" for i in range(51)]},
        {"search_max_queries": 0},
        {"search_max_queries": 51},
        {"search_max_pages": 101},
    ):
        r = await client.put("/api/v1/settings", json=base | change)
        assert r.status_code == 422, change


async def test_settings_normalizes_domains(client: httpx.AsyncClient) -> None:
    base = (await client.get("/api/v1/settings")).json()
    change = {
        "preferred_domains": ["https://WWW.Python.org/doc", "python.org", "Docs.Rs."],
        "search_provider_order": ["brave", "searxng"],
        "search_max_queries": 50,
        "search_max_pages": 100,
    }
    r = await client.put("/api/v1/settings", json=base | change)
    assert r.status_code == 200
    assert r.json()["preferred_domains"] == ["python.org", "docs.rs"]
    again = (await client.get("/api/v1/settings")).json()
    assert again["search_provider_order"] == ["brave", "searxng"]
    assert (again["search_max_queries"], again["search_max_pages"]) == (50, 100)


async def test_settings_study_defaults(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings")).json()
    assert (body["study_work_minutes"], body["study_break_minutes"]) == (50, 10)
    assert body["timezone"] == "Europe/Paris"


async def test_study_rhythm_and_timezone_roundtrip_and_bounds(client: httpx.AsyncClient) -> None:
    base = (await client.get("/api/v1/settings")).json()
    change = {"study_work_minutes": 25, "study_break_minutes": 0, "timezone": "America/New_York"}
    assert (await client.put("/api/v1/settings", json=base | change)).status_code == 200
    again = (await client.get("/api/v1/settings")).json()
    assert {key: again[key] for key in change} == change
    for bad in (
        {"study_work_minutes": 9},
        {"study_work_minutes": 121},
        {"study_break_minutes": -1},
        {"study_break_minutes": 61},
    ):
        r = await client.put("/api/v1/settings", json=base | bad)
        assert r.status_code == 422, bad


async def test_unknown_timezone_is_422_without_echo(client: httpx.AsyncClient) -> None:
    current = (await client.get("/api/v1/settings")).json()
    for zone in ("Mars/Olympus", "../../etc/Olympus", "", "Olympus" * 20):
        r = await client.put("/api/v1/settings", json={**current, "timezone": zone})
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
        assert "Olympus" not in r.text
