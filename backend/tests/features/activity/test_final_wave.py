"""Revue finale de la phase 8 (D173) : « offres lues » ne compte que les offres, un passage
abandonné ne promet plus de nouvel essai, une leçon est datée de son passage à « prête »."""

from sqlalchemy import select

from app.db.models.lessons import Lesson
from app.features.lessons.repository.lessons import LessonRepository
from tests.features.activity.support import Env, add_job, add_run, hours, set_lesson
from tests.features.activity.support import page as _page
from tests.features.study.conftest import seed


async def test_radar_title_counts_postings_not_pages(env: Env) -> None:
    await add_run(env, hours(1), read_count=21, not_postings=8, blocked_count=3)
    [item] = (await _page(env)).items
    assert item.title == "Relevé du radar : 13 offres lues, 3 bloquées"


async def test_failed_pass_with_attempts_left_promises_a_retry(env: Env) -> None:
    await add_job(env, hours(1), attempts=2)
    [item] = (await _page(env)).items
    assert item.title.endswith("nouvel essai au prochain passage.")


async def test_abandoned_or_exhausted_pass_promises_no_retry(env: Env) -> None:
    await add_job(env, hours(1), period="2026-W46", attempts=3, code="session_failed")
    await add_job(env, hours(2), period="2026-W47", attempts=1, code="abandoned")
    page = await _page(env)
    assert [item.title for item in page.items] == [
        "Un passage planifié a échoué (brief du matin) : abandonné, aucun nouvel essai.",
        "Un passage planifié a échoué (brief du matin) : abandonné, aucun nouvel essai.",
    ]


async def test_lesson_pdf_written_later_does_not_move_the_lesson_in_the_feed(env: Env) -> None:
    """Le PDF rangé après coup est une écriture technique : la leçon reste datée de son passage à
    « prête » (D173)."""
    seeded = await seed(env.app)
    lesson_id = seeded.lessons[0]
    await set_lesson(env, lesson_id, "ready", hours(1))
    async with env.factory() as db:
        assert await LessonRepository(db, env.user_id).set_pdf_key(lesson_id, "cle.pdf")
        assert not await LessonRepository(db, env.user_id).set_pdf_key(lesson_id, "autre.pdf")
        await db.commit()
        row = (await db.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one()
        assert row.pdf_key == "cle.pdf"
    [item] = [i for i in (await _page(env)).items if i.id == f"lesson:{lesson_id}:ready"]
    assert item.at == hours(1)
