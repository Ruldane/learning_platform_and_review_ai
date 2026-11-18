"""Programme écrit en direct : bornes du schéma (422 sans écho) et date de début."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.features.program.test_program_direct import SECRET, new_goal, program_body
from tests.support.direct import API, assert_no_agent


def refused(goal_id: str) -> list[dict[str, Any]]:
    """Corps refusés par le schéma ; les textes en faute portent SECRET."""
    base = program_body(goal_id)
    first = base["weeks"][0]
    bodies = [
        {**base, "title": SECRET * 20},
        {**base, "weeks": [{**first, "modules": []}]},
        {**base, "weeks": []},
        {**base, "weeks": [first] * 53},
        {**base, "weeks": [{**first, "modules": first["modules"] * 5}]},
        {**base, "weeks": [{**first, "theme": SECRET * 30}]},
        {**base, "weeks": [{**first, "objective": SECRET * 40}]},
        {"title": SECRET},
    ]
    for field, value in (
        ("tasks", []),
        ("skills", [SECRET * 40]),
        ("skills", []),
        ("title", SECRET * 30),
        ("prerequisites", [SECRET * 40]),
    ):
        copy = program_body(goal_id)
        copy["weeks"][0]["modules"][0][field] = value
        bodies.append(copy)
    for field, value in (
        ("minutes", 5),
        ("minutes", 500),
        ("type", SECRET),
        ("title", SECRET * 30),
        ("done_criterion", SECRET * 30),
    ):
        copy = program_body(goal_id)
        copy["weeks"][0]["modules"][0]["tasks"][0][field] = value
        bodies.append(copy)
    return bodies


async def test_direct_program_schema_limits_are_422_without_echo(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    goal_id = await new_goal(client)

    for body in refused(goal_id):
        r = await client.post(f"{API}/programs/direct", json=body)
        assert r.status_code == 422, body
        assert SECRET not in r.text
    assert (await client.get(f"{API}/programs")).json() == []
    await assert_no_agent(app)


@pytest.mark.parametrize("start", ["2026-11-17", "2000-01-03"])
async def test_direct_program_start_must_be_a_coming_monday(
    client: httpx.AsyncClient, start: str
) -> None:
    r = await client.post(
        f"{API}/programs/direct", json=program_body(await new_goal(client), start_date=start)
    )

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_start_date" and start not in r.text
