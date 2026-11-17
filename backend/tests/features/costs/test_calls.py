"""`GET /costs/calls` : le journal des agents (du plus récent au plus ancien, curseur, filtres,
bornes de `limit`, isolation, aucun écho, aucun journal)."""

import base64
import logging
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agents import LlmCall
from app.features.costs.service.calls import decode_cursor, encode_cursor
from tests.sessions_support import act_as

API = "/api/v1/costs/calls"
T0 = datetime(2026, 11, 10, 12, 0, 0, tzinfo=UTC)


async def seed_many(db: AsyncSession, user_id: str, count: int, **over: Any) -> None:
    """`count` appels espacés d'une seconde, le plus ancien en premier (`call-000`)."""
    for index in range(count):
        fields: dict[str, Any] = {
            "id": f"call-{index:03d}",
            "user_id": user_id,
            "created_at": T0 + timedelta(seconds=index),
            "graph": "capture",
            "agent": "analyst",
            "provider": "glm",
            "model": "glm-5.3-flash",
            "tokens_in": 10,
            "tokens_out": 5,
            "latency_ms": 120,
            "cost_usd": 0.01,
        }
        db.add(LlmCall(**{**fields, **over}))
    await db.commit()


async def test_calls_newest_first_with_cursor(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed_many(db_session, app.state.local_user_id, 120)
    first = (await client.get(API)).json()
    assert [item["id"] for item in first["items"]][:2] == ["call-119", "call-118"]
    assert len(first["items"]) == 50 and first["next_before"]
    second = (await client.get(API, params={"before": first["next_before"]})).json()
    assert len(second["items"]) == 50 and second["items"][0]["id"] == "call-069"
    third = (await client.get(API, params={"before": second["next_before"]})).json()
    assert len(third["items"]) == 20 and third["next_before"] is None
    seen = [item["id"] for page in (first, second, third) for item in page["items"]]
    # Aucun doublon, aucun trou.
    assert seen == [f"call-{index:03d}" for index in range(119, -1, -1)]


async def test_calls_item_shape_has_no_prompt(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed_many(db_session, app.state.local_user_id, 1, session_id="s-1", estimated=True)
    [item] = (await client.get(API)).json()["items"]
    assert item == {
        "id": "call-000",
        "at": "2026-11-10T12:00:00Z",
        "session_id": "s-1",
        "graph": "capture",
        "agent": "analyst",
        "provider": "glm",
        "model": "glm-5.3-flash",
        "tokens_in": 10,
        "tokens_out": 5,
        "latency_ms": 120,
        "cost_usd": 0.01,
        "estimated": True,
    }


async def test_calls_same_instant_are_not_skipped_nor_repeated(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    for index in range(5):
        db_session.add(
            LlmCall(
                id=f"same-{index}",
                user_id=app.state.local_user_id,
                created_at=T0,
                provider="glm",
                model="m",
            )
        )
    await db_session.commit()
    first = (await client.get(API, params={"limit": "2"})).json()
    second = (await client.get(API, params={"limit": "2", "before": first["next_before"]})).json()
    third = (await client.get(API, params={"limit": "2", "before": second["next_before"]})).json()
    ids = [i["id"] for page in (first, second, third) for i in page["items"]]
    assert ids == ["same-4", "same-3", "same-2", "same-1", "same-0"]
    assert third["next_before"] is None


async def test_calls_exact_page_has_no_next(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed_many(db_session, app.state.local_user_id, 50)
    body = (await client.get(API)).json()
    assert len(body["items"]) == 50 and body["next_before"] is None


async def test_calls_empty(client: httpx.AsyncClient) -> None:
    assert (await client.get(API)).json() == {"items": [], "next_before": None}


async def test_calls_filter_agent_and_graph(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    user = app.state.local_user_id
    await seed_many(db_session, user, 3)
    for index, (graph, agent) in enumerate([("council", "strategist"), ("council", "scribe")]):
        db_session.add(
            LlmCall(
                id=f"other-{index}",
                user_id=user,
                created_at=T0 + timedelta(minutes=1, seconds=index),
                graph=graph,
                agent=agent,
                provider="glm",
                model="m",
            )
        )
    await db_session.commit()
    by_agent = (await client.get(API, params={"agent": "scribe"})).json()["items"]
    assert [i["id"] for i in by_agent] == ["other-1"]
    by_graph = (await client.get(API, params={"graph": "council"})).json()["items"]
    assert [i["id"] for i in by_graph] == ["other-1", "other-0"]
    both = (await client.get(API, params={"graph": "council", "agent": "strategist"})).json()
    assert [i["id"] for i in both["items"]] == ["other-0"]
    none = (await client.get(API, params={"agent": "tutor"})).json()
    assert none == {"items": [], "next_before": None}


async def test_calls_empty_filter_finds_calls_without_agent_or_graph(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    """Le rapport range ces appels sous la clé `""` : le journal les retrouve avec elle."""
    user = app.state.local_user_id
    await seed_many(db_session, user, 2)
    rows = [
        ("no-agent", None, "capture"),
        ("no-graph", "analyst", None),
        ("no-both", None, None),
        ("blank-both", "", ""),
    ]
    for index, (call_id, agent, graph) in enumerate(rows):
        db_session.add(
            LlmCall(
                id=call_id,
                user_id=user,
                created_at=T0 + timedelta(minutes=1, seconds=index),
                graph=graph,
                agent=agent,
                provider="glm",
                model="m",
            )
        )
    await db_session.commit()
    no_agent = (await client.get(API, params={"agent": ""})).json()["items"]
    assert [i["id"] for i in no_agent] == ["blank-both", "no-both", "no-agent"]
    no_graph = (await client.get(API, params={"graph": ""})).json()["items"]
    assert [i["id"] for i in no_graph] == ["blank-both", "no-both", "no-graph"]
    both = (await client.get(API, params={"agent": "", "graph": ""})).json()["items"]
    assert [i["id"] for i in both] == ["blank-both", "no-both"]
    # Un nom d'agent ne retrouve jamais ces lignes.
    named = (await client.get(API, params={"agent": "analyst"})).json()["items"]
    assert "no-agent" not in [i["id"] for i in named] and "no-both" not in [i["id"] for i in named]


async def test_calls_filter_keeps_cursor(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed_many(db_session, app.state.local_user_id, 7)
    first = (await client.get(API, params={"agent": "analyst", "limit": "3"})).json()
    second = (
        await client.get(
            API, params={"agent": "analyst", "limit": "3", "before": first["next_before"]}
        )
    ).json()
    assert [i["id"] for i in second["items"]] == ["call-003", "call-002", "call-001"]


@pytest.mark.parametrize("limit", [1, 100])
async def test_calls_limit_bounds_are_accepted(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession, limit: int
) -> None:
    await seed_many(db_session, app.state.local_user_id, 101)
    r = await client.get(API, params={"limit": str(limit)})
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == limit and r.json()["next_before"]


@pytest.mark.parametrize("limit", ["0", "101", "-1", "abc", "", "5.5"])
async def test_calls_limit_out_of_bounds_is_422_without_echo(
    client: httpx.AsyncClient, limit: str
) -> None:
    r = await client.get(API, params={"limit": limit})
    assert r.status_code == 422
    assert r.json() == {
        "error": {
            "code": "validation_error",
            "message": "Requête invalide : vérifie les champs signalés.",
            "details": {"fields": ["limit"]},
        }
    }


def _cursor(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


@pytest.mark.parametrize(
    "cursor",
    [
        "pas-un-curseur-ECHO-XYZ",
        "!!!",
        _cursor("sans-barre-ECHO-XYZ"),
        _cursor("pas-une-date|call-1"),
        _cursor("2026-11-10T12:00:00|call-1"),  # sans fuseau
        _cursor("2026-11-10T12:00:00+00:00|"),  # sans identifiant
        _cursor("2026-11-10T12:00:00+00:00|ECHO-XYZ" + "x" * 80),  # identifiant trop long
        _cursor("0001-01-01T00:00:00+05:00|x"),  # hors de la plage des dates une fois en UTC
        _cursor("9999-12-31T23:59:59-05:00|x"),
        base64.urlsafe_b64encode(b"\xff\xfe\xfd|x").decode(),  # pas de l'UTF-8
    ],
)
async def test_bad_cursor_is_422_without_echo(client: httpx.AsyncClient, cursor: str) -> None:
    r = await client.get(API, params={"before": cursor})
    assert r.status_code == 422
    assert r.json() == {
        "error": {
            "code": "validation_error",
            "message": "Requête invalide : vérifie les champs signalés.",
            "details": {"fields": ["before"]},
        }
    }


async def test_calls_before_too_long_is_422(client: httpx.AsyncClient) -> None:
    r = await client.get(API, params={"before": "a" * 201})
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["before"]}


def test_cursor_round_trip_and_is_opaque() -> None:
    at = datetime(2026, 11, 10, 12, 0, 0, 123456, tzinfo=UTC)
    raw = encode_cursor(at, "call-7")
    assert "=" not in raw and "call-7" not in raw and "2026" not in raw
    assert decode_cursor(raw) == (at, "call-7")
    # Un instant avec un autre fuseau revient en UTC : même instant.
    other = datetime(2026, 11, 10, 13, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    assert decode_cursor(encode_cursor(other, "x"))[0] == other


async def test_calls_other_user_invisible(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed_many(db_session, app.state.local_user_id, 2)
    await seed_many(db_session, "autre-compte", 1, id="intrus-1", agent="analyst")
    ids = [item["id"] for item in (await client.get(API)).json()["items"]]
    assert ids == ["call-001", "call-000"]
    act_as(app, "autre-compte")
    assert [item["id"] for item in (await client.get(API)).json()["items"]] == ["intrus-1"]
    # Le curseur d'un autre compte ne donne accès à rien de plus.
    act_as(app, app.state.local_user_id)
    cursor = encode_cursor(T0 + timedelta(hours=1), "zzz")
    ids = [i["id"] for i in (await client.get(API, params={"before": cursor})).json()["items"]]
    assert "intrus-1" not in ids


async def test_calls_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    r = await client_google_mode.get(API)
    assert r.status_code == 401


async def test_calls_never_logged(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await seed_many(db_session, app.state.local_user_id, 3, agent="agent-secret-xyz")
    with caplog.at_level(logging.DEBUG, logger="app"):
        r = await client.get(API, params={"agent": "agent-secret-xyz", "before": "curseur-ECHO"})
        assert r.status_code == 422
        ok = await client.get(API, params={"agent": "agent-secret-xyz"})
        assert len(ok.json()["items"]) == 3
    assert "agent-secret-xyz" not in caplog.text and "curseur-ECHO" not in caplog.text
