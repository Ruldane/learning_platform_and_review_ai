"""The activity feed sources (P15, D163): one source is a function that reads a feature's
service, one line in `ACTIVITY_SOURCES`. Each source returns at most `limit` events in
`[after, before]` (bounds included: the feed drops the cursor ties itself), in no required
order; the merge is in `feed`. The texts are written here, by the code: a lesson or item title
is user data, never model text. A failed step never carries its error code. A project that is
validated or to resume (`project`, 8.10) only quotes its title, never the render."""

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
                link=f"/learn/lessons/{lesson.id}",
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
            link=f"/career/radar/{run.id}",
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
                link=f"/skills/portfolio/{project.id}",
            )
        )
    return items


async def ide_source(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[ActivityItem]:
    """A successful code session (first check); kind `project`: the icon of a proof (a kind
    specific to the IDE would change the contract and the home page, 10.I). Title: that of
    the session (user data, never model text)."""
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
            link="/memory",
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


# Each new source is one line here (the next phases add their own).
ACTIVITY_SOURCES: tuple[ActivitySource, ...] = (
    lessons_source,
    radar_source,
    brief_source,
    project_source,
    ide_source,
    memory_source,
    job_failures_source,
)
