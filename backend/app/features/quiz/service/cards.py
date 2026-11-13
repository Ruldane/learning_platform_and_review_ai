"""Fiches de révision espacée (SPEC F9, D101) : création dédoublonnée par recto, file du jour
(30 fiches au plus, 15 minutes) et avis. Les jours sont ceux de January (fuseau, D98).

Un avis est gardé par l'échéance (`due_date ≤ aujourd'hui local`) : le second de deux avis
simultanés trouve la fiche déjà repoussée (409 `card_not_due`). Deux échecs de suite sur les
fiches d'un acquis `valide` le font redescendre à `en_cours` (`record_review`) ; la mémoire le
reflète après le commit (`allow_lower`, seule baisse admise). Journaux : identifiants seulement,
jamais le recto ni le verso."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.study_schema import card_hash
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.study import CardSource
from app.features.memory.service.skill_levels import reflect_skill_level
from app.features.quiz.repository import FlashcardRepository
from app.features.quiz.schemas import DueQueue, FlashcardOut, ReviewOut
from app.features.quiz.service.runtime import QuizRuntime
from app.features.quiz.service.spacing import DAILY_CARDS, first_due, next_review, queue_room
from app.features.skills.service import SkillsService

logger = logging.getLogger(__name__)

FRONT_MAX = 2000
BACK_MAX = 2000
SKILL_MAX = 120


@dataclass(frozen=True)
class NewCard:
    front: str
    back: str
    skill: str | None
    module_id: str | None
    source: CardSource
    source_id: str | None


async def add_cards(db: AsyncSession, user_id: str, cards: Iterable[NewCard], today: date) -> int:
    """Écrit les fiches dont le recto est nouveau (dues demain) ; rend le nombre créé."""
    repo = FlashcardRepository(db, user_id)
    created = 0
    for card in cards:
        front = card.front.strip()[:FRONT_MAX]
        if not front:
            continue
        created += await repo.insert_once(
            front=front,
            back=card.back.strip()[:BACK_MAX],
            front_hash=card_hash(front),
            skill=card.skill[:SKILL_MAX] if card.skill else None,
            module_id=card.module_id,
            source=card.source,
            source_id=card.source_id,
            step=0,
            due_date=first_due(today),
        )
    return created


async def due_queue(rt: QuizRuntime, db: AsyncSession, user_id: str) -> DueQueue:
    """La file du jour : fiches dues, les plus en retard d'abord, dans la place qui reste."""
    today = await rt.today(db, user_id)
    repo = FlashcardRepository(db, user_id)
    reviewed = await repo.count_reviewed(today)
    cards = await repo.due(today, queue_room(reviewed))
    total = await repo.count_due(today)
    return DueQueue(
        cards=[FlashcardOut(id=c.id, front=c.front, back=c.back, skill=c.skill) for c in cards],
        reviewed_today=reviewed,
        daily_cards=DAILY_CARDS,
        remaining_due=max(0, total - len(cards)),
    )


async def due_skill_names(db: AsyncSession, user_id: str, today: date) -> set[str]:
    """Noms normalisés des compétences qui ont une fiche due (≤ `today`, jour de January) :
    prochaine action « Réviser » de la carte (D107). Lecture pour les autres features."""
    skills = await FlashcardRepository(db, user_id).due_skills(today)
    return {norm for norm in map(normalize_skill_name, skills) if norm}


def card_not_found() -> AppError:
    return AppError("card_not_found", "Fiche introuvable.", 404)


def card_not_due() -> AppError:
    return AppError("card_not_due", "Cette fiche n'est pas à revoir aujourd'hui.", 409)


async def _review(
    rt: QuizRuntime, db: AsyncSession, user_id: str, card_id: str, ok: bool
) -> tuple[ReviewOut, str | None]:
    today = await rt.today(db, user_id)
    repo = FlashcardRepository(db, user_id)
    card = await repo.get_fresh(card_id)
    if card is None:
        raise card_not_found()
    if card.due_date > today:
        raise card_not_due()
    step, due = next_review(card.step, ok, today)
    if not await repo.claim_review(card_id, today, step, due):
        raise card_not_due()
    demoted: str | None = None
    if card.skill:
        skills = SkillsService(db, user_id)
        if await skills.record_review(card.skill, ok) is not None:
            demoted = await skills.display_name(card.skill)
    out = ReviewOut(card_id=card_id, step=step, due_date=due, demoted_skill=demoted)
    return out, demoted


async def review_card(rt: QuizRuntime, user_id: str, card_id: str, ok: bool) -> ReviewOut:
    """Avis sur une fiche due : palier et échéance mis à jour (une erreur : demain local)."""
    async with rt.session_factory() as db:
        out, demoted = await _review(rt, db, user_id, card_id, ok)
        await db.commit()
    if demoted is not None:
        try:
            await reflect_skill_level(
                rt.memory,
                user_id,
                title=demoted,
                level="en_cours",
                author="user",
                session_id=None,
                reason="Deux échecs de suite sur les fiches de révision",
                allow_lower=True,
            )
        except Exception:
            logger.warning(
                "Rétrogradation non reflétée : utilisateur %s, fiche %s", user_id, card_id
            )
        logger.info("Acquis rétrogradé : utilisateur %s, fiche %s", user_id, card_id)
    return out
