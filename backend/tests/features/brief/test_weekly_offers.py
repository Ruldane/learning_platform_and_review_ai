from datetime import timedelta

from app.db.models.daily import Brief
from tests.features.brief.conftest import NOW, TODAY, Env
from tests.features.brief.support import add_run, posting, sections_for


async def test_weekly_offer_slots_survive_a_second_radar_run(env: Env) -> None:
    first = [f"https://jobs.example.org/offres/{number}" for number in range(1, 5)]
    async with env.rt.session_factory() as db:
        db.add(
            Brief(
                user_id=env.user_id,
                day=TODAY - timedelta(days=1),
                origin="schedule",
                sections={},
                offer_keys=first,
                created_at=NOW - timedelta(days=1),
            )
        )
        await db.commit()
    latest = await add_run(env, [posting(1, 99), posting(5, 83), posting(6, 76)])
    offers = (await sections_for(env))["offers"]
    [item] = offers["items"]
    assert item["title"] == "Poste 5"
    assert item["run_id"] == latest and item["offer_ref"] == "p5"
