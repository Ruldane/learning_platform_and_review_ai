"""Fiches de révision (SPEC F9, D101) : file du jour plafonnée à 30 (15 min) moins les fiches
déjà revues ; avis gardé par l'échéance (double avis = 409) ; échéance au lendemain LOCAL
(Review Focus n° 4) ; deux échecs de suite font redescendre un acquis `valide`."""

import asyncio
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.core.skills import evidence
from app.db.models.skills import Skill, UserSkill
from app.db.models.study import Flashcard
from app.features.memory.service.skill_levels import acquis_levels, reflect_skill_levels
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillsService
from tests.features.quiz.conftest import Seeded
from tests.sessions_support import act_as

API = "/api/v1"
TODAY = date(2026, 11, 17)  # jour local de `NOW` (conftest)


async def _cards(
    s: Seeded, n: int, *, due: date = TODAY, skill: str | None = None, reviewed: date | None = None
) -> list[str]:
    async with s.rt.session_factory() as db:
        rows = [
            Flashcard(
                user_id=s.user_id,
                front=f"Recto {n}-{i}-{due}",
                back="Verso",
                front_hash=f"{n}-{i}-{due}-{reviewed}",
                skill=skill,
                source="lesson",
                step=2,
                due_date=due,
                last_reviewed_on=reviewed,
            )
            for i in range(n)
        ]
        db.add_all(rows)
        await db.commit()
    return [row.id for row in rows]


async def _review(client: httpx.AsyncClient, card_id: str, result: str) -> httpx.Response:
    return await client.post(f"{API}/flashcards/{card_id}/review", json={"result": result})


async def test_due_queue_caps_at_30_minus_reviewed_today(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    await _cards(seeded, 40, due=TODAY - timedelta(days=1))
    await _cards(seeded, 5, due=TODAY + timedelta(days=3), reviewed=TODAY)
    await _cards(seeded, 3, due=TODAY + timedelta(days=1))  # pas encore dues
    body = (await client.get(f"{API}/flashcards/due")).json()
    assert len(body["cards"]) == 25
    assert (body["reviewed_today"], body["daily_cards"], body["remaining_due"]) == (5, 30, 15)
    assert set(body["cards"][0]) == {"id", "front", "back", "skill"}


@pytest.mark.parametrize(
    ("zone", "moment", "local_day"),
    [
        # 23 h 30 UTC = 0 h 30 le 13 à Paris : le lendemain local est le 14 (UTC dirait le 13).
        ("Europe/Paris", datetime(2026, 11, 12, 23, 30, tzinfo=UTC), date(2026, 11, 13)),
        # 23 h 30 à New York = 4 h 30 UTC le 13 : le lendemain local est le 13 (UTC dirait le 14).
        ("America/New_York", datetime(2026, 11, 13, 4, 30, tzinfo=UTC), date(2026, 11, 12)),
    ],
)
async def test_failed_card_is_due_next_local_day(
    client: httpx.AsyncClient, seeded: Seeded, zone: str, moment: datetime, local_day: date
) -> None:
    async with seeded.rt.session_factory() as db:
        settings = SettingsService(db, seeded.user_id)
        await settings.replace((await settings.get()).model_copy(update={"timezone": zone}))
        await db.commit()
    seeded.at(moment)
    [card_id] = await _cards(seeded, 1, due=local_day)
    r = await _review(client, card_id, "fail")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "card_id": card_id,
        "step": 0,
        "due_date": (local_day + timedelta(days=1)).isoformat(),
        "demoted_skill": None,
    }


async def test_double_review_is_409(client: httpx.AsyncClient, seeded: Seeded) -> None:
    [card_id] = await _cards(seeded, 1)
    first, second = await asyncio.gather(
        _review(client, card_id, "ok"), _review(client, card_id, "ok")
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    refused = first if first.status_code == 409 else second
    assert refused.json()["error"]["code"] == "card_not_due"
    accepted = first if first.status_code == 200 else second
    assert (accepted.json()["step"], accepted.json()["due_date"]) == (3, "2026-12-03")  # 16 j
    again = await _review(client, card_id, "fail")
    assert (again.status_code, again.json()["error"]["code"]) == (409, "card_not_due")
    async with seeded.rt.session_factory() as db:
        card = await db.get(Flashcard, card_id)
        assert card is not None and card.step == 3 and card.last_reviewed_on == TODAY


async def test_two_failures_demote_valide_to_en_cours(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    async with seeded.rt.session_factory() as db:
        proof = evidence("quiz", "q1", "Quiz", datetime(2026, 11, 16, tzinfo=UTC))
        await SkillsService(db, seeded.user_id).raise_levels(["Pandas"], "valide", proof)
        await db.commit()
    await reflect_skill_levels(
        seeded.rt.memory, seeded.user_id, [("Pandas", "valide")], author="examiner",
        session_id=None, reason="Quiz réussi",
    )  # fmt: skip
    first, second, third = await _cards(seeded, 3, skill="pandas")
    assert (await _review(client, first, "fail")).json()["demoted_skill"] is None
    assert (await _review(client, second, "ok")).json()["demoted_skill"] is None  # série remise
    assert (await _review(client, third, "fail")).json()["demoted_skill"] is None
    [fourth] = await _cards(seeded, 1, skill="PANDAS")
    assert (await _review(client, fourth, "fail")).json()["demoted_skill"] == "Pandas"
    async with seeded.rt.session_factory() as db:
        stmt = select(UserSkill.level, UserSkill.fail_streak).join(
            Skill, Skill.id == UserSkill.skill_id
        )
        assert (await db.execute(stmt)).one() == ("en_cours", 0)
        assert (await acquis_levels(db, seeded.user_id))["pandas"] == "en_cours"


async def test_review_of_unknown_or_foreign_card_is_404(
    client: httpx.AsyncClient, seeded: Seeded, app: FastAPI
) -> None:
    [card_id] = await _cards(seeded, 1)
    r = await _review(client, "inconnue", "ok")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "card_not_found")
    act_as(app, "un-autre-utilisateur")
    r = await _review(client, card_id, "ok")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "card_not_found")
    r = await client.post(f"{API}/flashcards/{card_id}/review", json={"result": "peut-etre"})
    assert r.status_code == 422 and "peut-etre" not in r.text
