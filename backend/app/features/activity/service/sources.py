"""Les sources du fil d'activité (P15, D163) : une source = une fonction qui lit le service d'une
feature, une ligne dans `ACTIVITY_SOURCES`. Chaque source rend au plus `limit` événements dans
`[after, before]` (bornes incluses : le fil écarte lui-même les ex æquo du curseur), sans ordre
imposé ; la fusion est dans `feed`. Les textes sont écrits ici, par
le code : un titre de leçon ou d'élément est une donnée de l'utilisatrice, jamais un texte de
modèle. Un passage en échec ne porte jamais son code d'erreur. Un projet validé ou à reprendre
(`project`, 8.10) ne cite que son titre, jamais le rendu.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.activity.schemas import ActivityItem
from app.features.brief.service.views import recent_briefs
from app.features.ledger.service.ledger import recent_failures
from app.features.lessons.service.lessons import recent_lessons
from app.features.memory.service.recent import recent_agent_writes
from app.features.projects.service.views import recent_projects
from app.features.radar.service.views import recent_runs

# (db, user_id, after, before, limit)
ActivitySource = Callable[
    [AsyncSession, str, datetime | None, datetime | None, int], Awaitable[list[ActivityItem]]
]

# Noms lisibles des agents (miroir du front, `messages/agents.ts`) et des tâches planifiées.
AGENT_NAMES: dict[str, str] = {
    "moderator": "Le Modérateur",
    "strategist": "Le Stratège",
    "practitioner": "Le Praticien",
    "scout": "L'Éclaireur",
    "skeptic": "Le Sceptique",
    "scribe": "Le Scribe",
    "writer": "Le Rédacteur",
    "verifier": "Le Vérificateur",
    "archivist": "L'Archiviste",
    "ats_reader": "Le Lecteur ATS",
    "recruiter": "Le Recruteur",
    "designer": "Le Maquettiste",
    "analyst": "L'Analyste",
    "examiner": "L'Examinateur",
    "interviewer": "L'Intervieweur",
    "tutor": "Le Tuteur",
    "tracker": "L'Assistant de suivi",
    "manager": "Le Manager",
    "colleague": "Le Futur collègue",
    "demo_proponent": "L'Avocat",
    "demo_critic": "Le Critique",
}
DEFAULT_AGENT = "Un agent"
JOB_NAMES: dict[str, str] = {
    "lessons_due": "préparation des leçons",
    "weekly_review": "bilan de la semaine",
    "skill_snapshots": "relevé des compétences",
    "reminders_due": "relances",
    "ats_refresh": "mise à jour des règles ATS",
    "market_radar": "radar du marché",
    "daily_brief": "brief du matin",
    "project_briefs": "énoncés des projets",
}
DEFAULT_JOB = "tâche de fond"


async def lessons_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    items: list[ActivityItem] = []
    for lesson in await recent_lessons(db, user_id, after, before, limit):
        label = "Leçon prête" if lesson.status == "ready" else "Leçon en échec"
        items.append(
            ActivityItem(
                id=f"lesson:{lesson.id}:{lesson.status}",
                kind="lesson",
                at=lesson.at,
                title=f"{label} : {lesson.title}",
                link=f"/apprendre/lecons/{lesson.id}",
            )
        )
    return items


async def radar_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    return [
        ActivityItem(
            id=f"radar:{run.id}:done",
            kind="radar",
            at=run.at,
            title=f"Relevé du radar : {run.read_count} offres lues, {run.blocked_count} bloquées",
            link=f"/carriere/radar/{run.id}",
        )
        for run in await recent_runs(db, user_id, after, before, limit)
    ]


async def brief_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    return [
        ActivityItem(
            id=f"brief:{brief.id}:ready",
            kind="brief",
            at=brief.at,
            title="Brief du jour prêt",
            link="/",
        )
        for brief in await recent_briefs(db, user_id, after, before, limit)
    ]


async def project_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    items: list[ActivityItem] = []
    for project in await recent_projects(db, user_id, after, before, limit):
        validated = project.verdict == "validated"
        label = "Projet validé" if validated else "Projet à reprendre"
        items.append(
            ActivityItem(
                id=(
                    f"project:{project.id}:validated"
                    if validated
                    else f"project:{project.id}:to_redo:{project.attempt}"
                ),
                kind="project",
                at=project.at,
                title=f"{label} : {project.title}",
                link=f"/competences/portfolio/{project.id}",
            )
        )
    return items


async def memory_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    return [
        ActivityItem(
            id=f"memory:{write.id}:{write.action}",
            kind="memory",
            at=write.at,
            title=(
                f"{AGENT_NAMES.get(write.author, DEFAULT_AGENT)} a écrit en mémoire : "
                f"{write.item_title}"
            ),
            detail=write.reason,
            link="/memoire",
        )
        for write in await recent_agent_writes(db, user_id, after, before, limit)
    ]


async def job_failures_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    return [
        ActivityItem(
            id=f"job_failed:{job.run_id}:{job.attempts}",
            kind="job_failed",
            at=job.finished_at or job.started_at,
            title=(
                f"Un passage planifié a échoué ({JOB_NAMES.get(job.name, DEFAULT_JOB)}) : "
                "nouvel essai au prochain passage."
            ),
        )
        for job in await recent_failures(db, user_id, after, before, limit)
    ]


# Une source de plus = une ligne ici (les phases suivantes ajoutent la leur).
ACTIVITY_SOURCES: tuple[ActivitySource, ...] = (
    lessons_source,
    radar_source,
    brief_source,
    project_source,
    memory_source,
    job_failures_source,
)
