"""Lectures du radar (14.2) : dernier relevé, liste (20, récent d'abord), détail avec classement,
évolution, alertes, offres, sites bloqués ; nombres réels dits (lues, bloquées, pas analysées)."""

from datetime import timedelta

import httpx
from fastapi import FastAPI

from tests.features.radar.support import NOW, Radar, link
from tests.features.skills.support import add_skill

API = "/api/v1/radar"


async def test_run_detail_has_the_real_counts_ranking_alerts_and_offers(
    client: httpx.AsyncClient, app: FastAPI, radar: Radar
) -> None:
    me = app.state.local_user_id
    first = await radar.analyzed_run([["Python", "Linux"]] * 10, user=me)
    radar.rt.now = lambda: NOW + timedelta(days=7)
    run_id = await radar.new_run(me)
    await radar.read(run_id, 14, user=me)
    for number in (1, 2, 3):
        await radar.store.read_posting(me, "s", run_id, link(number, "ferme.example.org"))
    await radar.store.read_posting(me, "s", run_id, link(9, "autre.example.org"))
    items = [["Python"]] * 10 + [["Rust"]]
    await radar.extract(run_id, items, user=me)
    await radar.store.finalize(me, "s", run_id)
    body = (await client.get(f"{API}/runs/{run_id}")).json()
    assert (
        body["status"] == "done" and body["trigger"] == "manual" and body["role"] == "Ingénieur IA"
    )
    assert (body["read_count"], body["blocked_count"], body["analyzed"]) == (14, 4, 11)
    assert (body["not_postings"], body["not_analyzed"]) == (0, 3)  # 14 lues, 11 analysées
    assert body["low_sample"] is True
    assert body["blocked_domains"] == [
        {"domain": "ferme.example.org", "count": 3},
        {"domain": "autre.example.org", "count": 1},
    ]
    assert body["previous"]["id"] == first
    python = next(t for t in body["ranking"] if t["skill"] == "Python")
    assert python["count"] == 10 and python["delta_share"] == -9 and python["new"] is False
    assert next(t for t in body["ranking"] if t["skill"] == "Rust")["new"] is True
    assert [a["skill"] for a in body["alerts"]] == ["Python"]
    assert len(body["offers"]) == 11
    assert {"url", "title", "company", "level", "remote", "salary", "score"} <= set(
        body["offers"][0]
    )
    assert [o["score"] for o in body["offers"]] == sorted(
        (o["score"] for o in body["offers"]), reverse=True
    )
    assert body["error_code"] is None and body["finished_at"] is not None


async def test_latest_gives_the_latest_finished_run_and_the_defaults(
    client: httpx.AsyncClient, app: FastAPI, radar: Radar
) -> None:
    me = app.state.local_user_id
    empty = (await client.get(f"{API}/latest")).json()
    assert empty == {"defaults": {"role": "", "zone": "France"}, "running": None, "latest": None}
    done = await radar.analyzed_run([["Python"]] * 3, user=me)
    running = await radar.open_run(me, role="En cours")
    latest = (await client.get(f"{API}/latest")).json()
    assert latest["latest"]["id"] == done and latest["running"]["id"] == running


async def test_list_is_recent_first_and_capped_at_twenty(
    client: httpx.AsyncClient, app: FastAPI, radar: Radar
) -> None:
    me = app.state.local_user_id
    ids = [
        await radar.new_run(me, status="done", created_at=NOW + timedelta(days=n))
        for n in range(23)
    ]
    listed = (await client.get(f"{API}/runs")).json()
    assert [item["id"] for item in listed] == ids[::-1][:20]
    assert set(listed[0]) == {
        "id",
        "role",
        "zone",
        "status",
        "trigger",
        "created_at",
        "finished_at",
        "error_code",
        "read_count",
        "blocked_count",
        "analyzed",
        "low_sample",
    }


async def test_unknown_run_is_a_404(client: httpx.AsyncClient) -> None:
    missing = await client.get(f"{API}/runs/inconnu")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "radar_run_not_found"


async def test_skill_map_demand_from_latest_run(
    client: httpx.AsyncClient, app: FastAPI, radar: Radar
) -> None:
    me = app.state.local_user_id
    await add_skill(radar.factory, me, "Python", "Langages")
    await add_skill(radar.factory, me, "Rust", "Langages")
    before = (await client.get("/api/v1/skills/graph")).json()
    assert [n["demand"] for n in before["nodes"]] == [None, None]
    await radar.analyzed_run([["Python"]] * 4 + [["Linux"]] * 6, user=me)
    nodes = {
        n["name"]: n["demand"] for n in (await client.get("/api/v1/skills/graph")).json()["nodes"]
    }
    assert nodes["Python"] == 0.4 and nodes["Rust"] == 0.0
