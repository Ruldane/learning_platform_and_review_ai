"""Les rubriques du brief calculées par le code (P11, D162) : bloc d'étude, révisions, relances,
nouvelles offres du radar, avancement de la semaine. Aucun modèle ici : chaque rubrique est un fait
lu dans une autre feature (leur service), figé en JSON dans le brief du jour.

Une rubrique sans objet vaut `None` (aucun bloc prévu, aucun programme validé) ; les nombres
(`reviews`, `reminders`) valent 0. `offers.items[*].key` (le lien normalisé) et `week.best_quiz`
sont des détails internes du brief, jamais rendus par l'API : l'un nourrit « déjà montré » des 7
jours suivants, l'autre les faits du conseil. Chaque rubrique est calculée à part (savepoint) : une
source en panne rend la rubrique vide et la nomme dans `unavailable`, jamais une erreur 500 pour
tout l'écran du matin (D173). Journaux : le nom de la rubrique et la classe de l'exception."""

import logging
from collections.abc import Awaitable
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import week_start
from app.features.applications.service.reminders import list_reminders
from app.features.brief.repository import BriefRepository
from app.features.brief.schemas import (
    BlockRubric,
    BriefBlockTask,
    OfferItem,
    OffersRubric,
    ReminderItem,
    RemindersRubric,
    ReviewsRubric,
    WeekRubric,
)
from app.features.brief.service.rules import REMINDERS_MAX, SHOWN_BRIEFS, new_offers
from app.features.brief.service.runtime import BriefRuntime
from app.features.program.service.programs import list_programs
from app.features.quiz.service.cards import due_queue
from app.features.radar.service.views import offers_since
from app.features.replan.service.facts import week_facts
from app.features.study.service.block import block_of_day
from app.features.study.service.view import summary


async def _block(db: AsyncSession, user_id: str, today: date) -> dict[str, Any] | None:
    block = await block_of_day(db, user_id, today)
    if block is None:
        return None
    return BlockRubric(
        module_title=block.module_title,
        lesson_id=block.lesson_id,
        lesson_title=block.lesson_title,
        minutes=sum(task.minutes for task in block.tasks),
        tasks=[BriefBlockTask(title=task.title, minutes=task.minutes) for task in block.tasks],
    ).model_dump(mode="json")


async def _reviews(rt: BriefRuntime, db: AsyncSession, user_id: str) -> dict[str, Any]:
    queue = await due_queue(rt.quiz, db, user_id)
    return ReviewsRubric(queue=len(queue.cards), remaining=queue.remaining_due).model_dump()


async def _reminders(rt: BriefRuntime, user_id: str) -> dict[str, Any]:
    due = await list_reminders(rt.applications, user_id, due=True)
    return RemindersRubric(
        due=len(due),
        items=[
            ReminderItem(
                reminder_id=item.id,
                application_id=item.application_id,
                company=item.company,
                title=item.title,
                kind=item.kind,
                due_on=item.due_on,
            )
            for item in due[:REMINDERS_MAX]
        ],
    ).model_dump(mode="json")


async def _offers(db: AsyncSession, user_id: str, today: date) -> dict[str, Any]:
    """Les offres des relevés finis depuis le brief précédent (ou du dernier relevé, sans brief
    avant), au score d'au moins 70, ni déjà montrées dans les 7 derniers briefs ni déjà saisies."""
    repo = BriefRepository(db, user_id)
    earlier = await repo.before(today, SHOWN_BRIEFS)
    postings = await offers_since(db, user_id, earlier[0].created_at if earlier else None)
    shown = {str(key) for brief in earlier for key in brief.offer_keys}
    chosen = new_offers(postings, shown, await repo.known_keys())
    rubric = OffersRubric(
        run_id=str(chosen[0]["run_id"]) if chosen else None,
        items=[
            OfferItem(
                url=str(posting["url"]),
                title=posting.get("title"),
                company=posting.get("company"),
                score=posting["score"],
            )
            for posting in chosen
        ],
    ).model_dump()
    for item, posting in zip(rubric["items"], chosen, strict=True):
        item["key"] = posting["url_key"]
    return rubric


async def _week(
    rt: BriefRuntime, db: AsyncSession, user_id: str, today: date
) -> dict[str, Any] | None:
    """La semaine locale du programme validé le plus récent ; la série vient du résumé d'étude."""
    programs = await list_programs(db, user_id)
    current = next((program for program in programs if program.status == "validated"), None)
    if current is None:
        return None
    facts = await week_facts(db, user_id, current.id, week_start(today))
    rubric = WeekRubric(
        planned_minutes=facts.planned_minutes,
        done_minutes=facts.done_minutes,
        tasks_done=facts.tasks_done,
        tasks_total=facts.tasks_planned,
        study_minutes=facts.study_minutes,
        streak_days=(await summary(rt.study, db, user_id)).streak_days,
    ).model_dump()
    rubric["best_quiz"] = max(facts.quiz_scores) if facts.quiz_scores else None
    return rubric


logger = logging.getLogger(__name__)

# Ce que vaut une rubrique dont la source est en panne : vide, jamais inventée.
_EMPTY: dict[str, Any] = {
    "block": None,
    "reviews": {"queue": 0, "remaining": 0},
    "reminders": {"due": 0, "items": []},
    "offers": {"run_id": None, "items": []},
    "week": None,
}


async def _isolated(db: AsyncSession, name: str, build: Awaitable[Any], failed: list[str]) -> Any:
    """La rubrique `name`, dans son propre savepoint : en cas de panne, sa valeur vide et son nom
    dans `failed` (la transaction reste valide pour les rubriques suivantes)."""
    try:
        async with db.begin_nested():
            return await build
    except Exception as exc:
        logger.warning("Brief : rubrique %s indisponible (%s)", name, type(exc).__name__)
        failed.append(name)
        return _EMPTY[name]


async def build_sections(
    rt: BriefRuntime, db: AsyncSession, user_id: str, today: date
) -> dict[str, Any]:
    """Les rubriques du code (`BRIEF_KEYS`) du jour local `today`, plus `unavailable` (les
    rubriques en panne) seulement s'il y en a."""
    failed: list[str] = []
    sections: dict[str, Any] = {
        "block": await _isolated(db, "block", _block(db, user_id, today), failed),
        "reviews": await _isolated(db, "reviews", _reviews(rt, db, user_id), failed),
        "reminders": await _isolated(db, "reminders", _reminders(rt, user_id), failed),
        "offers": await _isolated(db, "offers", _offers(db, user_id, today), failed),
        "week": await _isolated(db, "week", _week(rt, db, user_id, today), failed),
    }
    if failed:
        sections["unavailable"] = failed
    return sections
