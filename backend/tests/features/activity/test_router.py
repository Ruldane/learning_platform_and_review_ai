"""`GET /activity?after=&before=&limit=` (14.2, D163) : la forme rendue, les bornes, le plafond de
50, une 422 qui n'écho rien."""

import httpx

from tests.features.activity.support import (
    API,
    Env,
    add_brief,
    add_job,
    add_run,
    add_write,
    hours,
    minutes,
)


async def test_get_activity_shape_and_bounds(client: httpx.AsyncClient, env: Env) -> None:
    run_id = await add_run(env, hours(2))
    brief_id = await add_brief(env, hours(3))
    await add_write(env, hours(1), author="user")  # exclue
    body = (await client.get(API)).json()
    assert [item["id"] for item in body["items"]] == [
        f"brief:{brief_id}:ready",
        f"radar:{run_id}:done",
    ]
    assert body["items"][0] == {
        "id": f"brief:{brief_id}:ready",
        "kind": "brief",
        "at": "2026-11-17T09:00:00Z",
        "title": "Daily brief ready",
        "detail": None,
        "link": "/",
    }
    assert body["latest_at"] == "2026-11-17T09:00:00Z"
    after = (await client.get(API, params={"after": hours(2).isoformat()})).json()
    assert [item["kind"] for item in after["items"]] == ["brief"]
    naive = (await client.get(API, params={"after": "2026-11-17T08:00:00"})).json()  # lu en UTC
    assert [item["kind"] for item in naive["items"]] == ["brief"]
    before = (await client.get(API, params={"before": hours(3).isoformat()})).json()
    assert [item["kind"] for item in before["items"]] == ["radar"]
    empty = (await client.get(API, params={"after": hours(3).isoformat()})).json()
    assert empty == {"items": [], "latest_at": None}


async def test_limit_is_capped_and_validated(client: httpx.AsyncClient, env: Env) -> None:
    for number in range(55):
        await add_write(env, minutes(number))
    assert len((await client.get(API)).json()["items"]) == 30
    assert len((await client.get(API, params={"limit": 100})).json()["items"]) == 50
    assert len((await client.get(API, params={"limit": 3})).json()["items"]) == 3
    bad = await client.get(API, params={"limit": 0, "after": "pas une date"})
    assert bad.status_code == 422
    assert "pas une date" not in bad.text


async def test_job_failures_in_the_feed(client: httpx.AsyncClient, env: Env) -> None:
    await add_job(env, hours(1), code="secret_error_code")
    body = (await client.get(API)).json()
    assert [item["kind"] for item in body["items"]] == ["job_failed"]
    assert "secret_error_code" not in str(body)


async def test_cursor_params_page_through_ties(client: httpx.AsyncClient, env: Env) -> None:
    for number in range(4):
        await add_write(env, hours(2), title=f"Ex æquo {number}")
    seen: list[str] = []
    params: dict[str, object] = {"limit": 3}
    while True:
        body = (await client.get(API, params=params)).json()
        if not body["items"]:
            break
        seen += [item["id"] for item in body["items"]]
        last = body["items"][-1]
        params = {"limit": 3, "before": last["at"], "before_id": last["id"]}
    assert len(seen) == 4 and len(set(seen)) == 4
    first = (await client.get(API, params={"limit": 2})).json()["items"][0]
    nothing = await client.get(API, params={"after": first["at"], "after_id": first["id"]})
    assert nothing.json()["items"] == []
