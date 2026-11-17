"""L'aperçu de la demande « À confirmer » (relecture 10.B2, I1) : toute la requête, sa cible,
jamais un secret."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap_mcp import install_adapter
from app.mcp.confirm import preview_fields
from tests.agents.graphs_for_tests import TEST_GRAPHS
from tests.mcp.adapter_support import FEATURES, SECRET_KEY_TEXT, add_probe, call, declarations
from tests.mcp.support import API, Mcp
from tests.mcp.test_confirmations import make_application, pend

Factory = async_sessionmaker[AsyncSession]


async def shown(amcp: Mcp) -> dict[str, Any]:
    """La première demande de la liste, telle que January la voit."""
    listed = (await amcp.http.get(f"{API}/mcp/confirmations")).json()
    assert listed, "aucune demande"
    item: dict[str, Any] = listed[0]
    return item


# --- I1 : confirmer en voyant -----------------------------------------------------------------


async def test_confirmation_shows_the_whole_request(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    app_id = await make_application(client)
    long_text = "x" * 600
    await pend(amcp, writer, app_id, text=long_text)

    request = (await shown(amcp))["request"]

    assert request["method"] == "POST"
    assert request["route"] == "/applications/{application_id}/events"
    assert "Fictive" in request["target_label"] and "Dev" in request["target_label"]
    by_name = {field["name"]: field["value_preview"] for field in request["fields"]}
    assert by_name["kind"] == "note"
    assert by_name["text"] == "x" * 500 + "…" and request["truncated"] is True


async def test_confirmation_shows_objects_as_compact_json_and_hides_secrets(
    amcp: Mcp, writer: str
) -> None:
    data = {"experiences": [{"role": "Inventé", "note": SECRET_KEY_TEXT}]}
    await call(amcp, writer, "profile_update", {"data": data})

    request = (await shown(amcp))["request"]

    assert request["method"] == "PUT" and request["route"] == "/profile"
    assert request["target_label"] is None and request["truncated"] is False
    (field,) = request["fields"]
    assert field["name"] == "data"
    assert field["value_preview"] == '{"experiences":[{"role":"Inventé","note":"***"}]}'
    assert SECRET_KEY_TEXT not in str(await amcp.http.get(f"{API}/mcp/confirmations"))


async def test_confirmation_without_a_readable_target_has_no_label(amcp: Mcp, writer: str) -> None:
    await call(amcp, writer, "probe_who", {})

    request = (await shown(amcp))["request"]

    assert request["route"] == "/_probe/who" and request["target_label"] is None
    assert request["fields"] == []


async def test_confirmation_target_label_from_the_web_is_fenced(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    add_probe(app)
    models = {name: spec.input_model for name, spec in TEST_GRAPHS.items()}
    install_adapter(app, declarations(get_untrusted=("company", "title")), models)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        amcp = Mcp(http)
        token = await amcp.token(FEATURES, "write")
        app_id = await make_application(client)
        await pend(amcp, token, app_id)

        label = (await shown(amcp))["request"]["target_label"]

    assert "<donnee_non_fiable>Fictive</donnee_non_fiable>" in label


def test_preview_fields_caps_each_value_and_the_whole() -> None:
    from app.mcp.arguments import ToolRequest  # noqa: PLC0415

    body = {f"champ_{index}": "y" * 1000 for index in range(10)}
    fields, truncated = preview_fields(ToolRequest("POST", "/x", {"q": "a"}, body))

    assert [field[0] for field in fields] == ["q", *body]  # tous les noms, toujours
    assert all(len(value) <= 501 for _, value in fields)
    assert sum(len(value) for _, value in fields) <= 4_000 + len(fields)
    assert truncated is True
    small, flag = preview_fields(ToolRequest("POST", "/x", {}, {"a": 1, "b": [1, "z"]}))
    assert small == [("a", "1"), ("b", '[1,"z"]')] and flag is False
