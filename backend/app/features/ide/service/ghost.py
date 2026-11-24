"""Exercise version and summary of personal checks, read-only."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.core.practice import PracticeSummary, compare_versions, content_version
from app.db.base import utcnow
from app.db.models.ide import IdeExercise, IdeRun
from app.features.capture.service.journal import add_entry
from app.features.ide.repository import RunRepository, SessionRepository
from app.features.ide.service.errors import session_not_found
from app.features.settings.service import SettingsService


def exercise_version(exercise: IdeExercise) -> str:
    return content_version(exercise.statement, exercise.entry, exercise.files)


def _summary(run: IdeRun, current: str | None, previous: str | None) -> PracticeSummary:
    passed = run.exit_code == 0 if run.status == "done" and run.exit_code is not None else None
    return PracticeSummary(
        id=run.id,
        created_at=run.created_at,
        version=compare_versions(current, previous),
        elapsed_ms=run.duration_ms,
        errors=int(not passed) if passed is not None else None,
        progress=int(passed) if passed is not None else None,
        total=1 if passed is not None else None,
    )


async def record_finished_check(db: AsyncSession, run: IdeRun) -> None:
    settings = await SettingsService(db, run.user_id).get()
    day = utcnow().astimezone(user_zone(settings.timezone)).date()
    text = "Code check passed." if run.exit_code == 0 else "Code check finished with a failure."
    await add_entry(
        db,
        run.user_id,
        kind="ide_check",
        text=text,
        occurred_on=day,
        ref_key=f"ide-check:{run.id}",
        data={"ide_session_id": run.session_id, "ide_run_id": run.id},
    )


async def read_history(
    db: AsyncSession, user_id: str, session_id: str, run_id: str | None = None
) -> list[PracticeSummary]:
    session = await SessionRepository(db, user_id).get_fresh(session_id)
    if session is None:
        raise session_not_found()
    if session.exercise_id is None:
        return []
    current = session.exercise_version
    # Checks compare sessions opened on the same starting exercise.
    checks = await RunRepository(db, user_id).recent_for_exercise(
        session.exercise_id, current, run_id
    )
    return [_summary(run, current, previous) for run, previous in checks]
