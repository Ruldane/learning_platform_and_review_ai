"""Repères de reprise entièrement fictifs."""

from datetime import timedelta

from fastapi import FastAPI

from app.core.skills import normalize_skill_name
from app.db.base import new_id, utcnow
from app.db.models.skills import Skill, UserSkill
from app.db.models.study import Flashcard, StudySession
from app.features.conversations.service import ensure_conversation
from app.features.study.service.training import thread_for
from tests.features.interprogram_planning.support import seed_task

ACQUIRED = "Validation des données"
UNFINISHED = "Agrégation avancée"
DUE = "Comment reconnaître une donnée manquante ?"
ANSWER = "Comparer explicitement avec l’absence de valeur."


async def seed_return(app: FastAPI, user_id: str | None = None) -> tuple[str, str]:
    owner = user_id or app.state.local_user_id
    now = utcnow()
    prior = now - timedelta(days=10)
    async with app.state.session_factory() as db:
        block = StudySession(
            user_id=owner,
            kind="training",
            mode="direct",
            status="finished",
            created_at=prior - timedelta(minutes=14),
            ended_at=prior,
            minutes=14,
        )
        db.add(block)
        await db.flush()
        await ensure_conversation(db, owner, thread_for(block.id))
        for name, level in ((ACQUIRED, "valide"), (UNFINISHED, "en_cours")):
            row = Skill(id=new_id(), user_id=owner, name=name, norm_name=normalize_skill_name(name))
            db.add(row)
            await db.flush()
            db.add(UserSkill(user_id=owner, skill_id=row.id, level=level))
        db.add_all(
            [
                Flashcard(
                    user_id=owner,
                    front=DUE,
                    back=ANSWER,
                    front_hash=new_id(),
                    skill=ACQUIRED,
                    source="study",
                    due_date=prior.date(),
                ),
                Flashcard(
                    user_id=owner,
                    front="Fiche encore future",
                    back="Réponse",
                    front_hash=new_id(),
                    source="study",
                    due_date=(now + timedelta(days=7)).date(),
                ),
            ]
        )
        _, task_id = await seed_task(db, owner, "Tâche déjà planifiée", 45)
        await db.commit()
        return block.id, task_id
