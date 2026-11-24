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
from app.features.ide.service.sessions import recent_passes
from app.features.ledger.service.ledger import recent_failures
from app.features.ledger.service.periods import MAX_ATTEMPTS
from app.features.lessons.service.lessons import recent_lessons
from app.features.memory.service.recent import recent_agent_writes
from app.features.projects.service.views import recent_projects
from app.features.radar.service.views import recent_runs

# (db, user_id, after, before, limit)
ActivitySource = Callable[
    [AsyncSession, str, datetime | None, datetime | None, int], Awaitable[list[ActivityItem]]
]

# Display names for agents (matching `messages/agents.ts`) and scheduled jobs.
AGENT_NAMES: dict[str, str] = {
    "moderator": "Moderator",
    "strategist": "Strategist",
    "practitioner": "Practitioner",
    "scout": "Scout",
    "skeptic": "Skeptic",
    "scribe": "Scribe",
    "writer": "Writer",
    "verifier": "Verifier",
    "archivist": "Archivist",
    "ats_reader": "ATS reader",
    "recruiter": "Recruiter",
    "designer": "Layout designer",
    "analyst": "Analyst",
    "examiner": "Examiner",
    "interviewer": "Interviewer",
    "tutor": "Tutor",
    "tracker": "Tracking assistant",
    "manager": "Manager",
    "colleague": "Future colleague",
    "demo_proponent": "Advocate",
    "demo_critic": "Critic",
    "professor": "Professor",
    "exercise_writer": "Exercise author",
    "boss_reviewer": "Challenge reviewer",
    "code_prosecutor": "Prosecutor",
    "code_defender": "Defender",
    "oncall_reviewer": "Operations lead",
    "lesson_professor": "Lesson tutor",
    "training_tutor": "Training tutor",
    "brain_librarian": "Knowledge librarian",
    "podcast_host": "Podcast host",
    "offers_adviser": "Offers assistant",
}
DEFAULT_AGENT = "An agent"
JOB_NAMES: dict[str, str] = {
    "lessons_due": "lesson preparation",
    "weekly_review": "weekly review",
    "skill_snapshots": "skills snapshot",
    "reminders_due": "follow-up reminders",
    "ats_refresh": "ATS rules update",
    "market_radar": "market radar",
    "daily_brief": "morning brief",
    "project_briefs": "project briefs",
}
DEFAULT_JOB = "background job"


async def lessons_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    items: list[ActivityItem] = []
    for lesson in await recent_lessons(db, user_id, after, before, limit):
        label = "Lesson ready" if lesson.status == "ready" else "Lesson failed"
        items.append(
            ActivityItem(
                id=f"lesson:{lesson.id}:{lesson.status}",
                kind="lesson",
                at=lesson.at,
                title=f"{label}: {lesson.title}",
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
            title=f"Radar scan: {run.offers_read} offers read, {run.blocked_count} blocked",
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
            title="Daily brief ready",
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
        label = "Project approved" if validated else "Project needs revision"
        items.append(
            ActivityItem(
                id=(
                    f"project:{project.id}:validated"
                    if validated
                    else f"project:{project.id}:to_redo:{project.ref}"
                ),
                kind="project",
                at=project.at,
                title=f"{label}: {project.title}",
                link=f"/competences/portfolio/{project.id}",
            )
        )
    return items


async def ide_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    """Une séance de code réussie (première vérification) ; genre `project` : l'icône d'une preuve
    (un genre propre à l'IDE changerait le contrat et l'accueil, 10.I). Titre : celui de la séance
    (donnée de l'utilisatrice, jamais un texte de modèle)."""
    return [
        ActivityItem(
            id=f"ide:{item.id}:passed",
            kind="project",
            at=item.at,
            title=f"Coding exercise passed: {item.title}",
            link=f"/code/{item.id}",
        )
        for item in await recent_passes(db, user_id, after, before, limit)
    ]


async def memory_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    return [
        ActivityItem(
            id=f"memory:{write.id}:{write.action}",
            kind="memory",
            at=write.at,
            title=(
                f"{AGENT_NAMES.get(write.author, DEFAULT_AGENT)} wrote to memory: "
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
                f"Scheduled run failed ({JOB_NAMES.get(job.name, DEFAULT_JOB)}). "
                + (
                    "No further attempts."
                    if job.attempts >= MAX_ATTEMPTS or job.error_code == "abandoned"
                    else "Will retry on the next run."
                )
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
    ide_source,
    memory_source,
    job_failures_source,
)
