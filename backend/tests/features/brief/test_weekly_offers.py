from datetime import UTC, datetime, timedelta

from app.db.models.daily import Brief
from tests.features.brief.conftest import NOW, TODAY, Env
from tests.features.brief.support import add_run, posting, sections_for


async def test_weekly_offer_rank_changes_after_publishing_five_offers(env: Env) -> None:
    previous = [posting(number, 75 - number) for number in range(1, 6)]
    yesterday = NOW - timedelta(days=1)
    await add_run(env, previous, finished_at=yesterday - timedelta(hours=1))
    async with env.rt.session_factory() as db:
        db.add(
            Brief(
                user_id=env.user_id,
                day=TODAY - timedelta(days=1),
                origin="schedule",
                sections={},
                offer_keys=[offer["key"] for offer in previous],
                created_at=yesterday,
            )
        )
        await db.commit()
    run = await add_run(env, [posting(1, 91), posting(6, 99), posting(7, 70)])
    offers = (await sections_for(env))["offers"]
    [item] = offers["items"]
    assert item["title"] == "Poste 6"
    assert item["run_id"] == run and item["offer_ref"] == "p6"


async def test_first_brief_combines_only_runs_inside_local_week_so_far(env: Env) -> None:
    # Lundi minuit à Paris, encore dimanche côté UTC.
    monday = datetime(2026, 11, 15, 23, tzinfo=UTC)
    await add_run(env, [posting(9, 100)], finished_at=monday - timedelta(seconds=1))
    first = await add_run(env, [posting(1, 98)], finished_at=monday)
    latest = await add_run(env, [posting(2, 95)])
    await add_run(env, [posting(8, 100)], finished_at=NOW + timedelta(seconds=1))
    offers = (await sections_for(env))["offers"]
    assert [(item["run_id"], item["offer_ref"]) for item in offers["items"]] == [
        (first, "p1"),
        (latest, "p2"),
    ]
