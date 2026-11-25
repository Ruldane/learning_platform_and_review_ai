"""Transactional opening of the trial and the user's verdict."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.code_trial_port import GRAPH, CodePleading
from app.core.caller import Caller
from app.core.errors import AppError
from app.core.played import inherit_source
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.code_trial import CodeTrial
from app.features.code_trial.repository import TrialRepository, missing
from app.features.code_trial.schemas import TrialOpened, TrialStatus, TrialVerdict, TrialView
from app.features.code_trial.snapshot import excerpts, python_files
from app.features.ide.service import IdeService
from app.features.sessions.service import session_facts


def project_reader(db: AsyncSession, user_id: str) -> IdeService:
    return IdeService(db, user_id, None, Caller("app", "code trial"))


def _verdict(row: CodeTrial) -> TrialVerdict | None:
    if row.verdict_choice is not None and row.verdict_reason is not None:
        return TrialVerdict.model_validate(
            {"choice": row.verdict_choice, "reason": row.verdict_reason}
        )
    return None


async def _running(db: AsyncSession, row: CodeTrial) -> bool:
    session = await session_facts(db, row.user_id, row.session_id)
    return session is not None and session.status in OPEN_SESSION_STATES


async def _view(db: AsyncSession, row: CodeTrial, current_version: int) -> TrialView:
    verdict = _verdict(row)
    status: TrialStatus
    if verdict is not None:
        status = "decided"
    elif row.pleadings:
        status = "ready"
    else:
        status = "running" if await _running(db, row) else "failed"
    return TrialView(
        id=row.id,
        session_id=row.session_id,
        title=row.title,
        files_version=row.files_version,
        current=row.files_version == current_version,
        file_count=len(row.snapshot),
        status=status,
        pleadings=[CodePleading.model_validate(item) for item in row.pleadings or ()],
        verdict=verdict,
    )


class _AlreadyOpen(Exception):
    def __init__(self, row: CodeTrial) -> None:
        self.started = TrialOpened(trial_id=row.id, session_id=row.session_id)


async def open_trial(
    launcher: SessionLauncher, db: AsyncSession, user_id: str, project_id: str
) -> TrialOpened:
    project = await project_reader(db, user_id).get_session(project_id)
    # Stable per account/version, including two simultaneous openings.
    trial_id = str(
        uuid5(NAMESPACE_URL, f"tremplin/code-trial/{user_id}/{project_id}/{project.files_version}")
    )

    async def prepare(write: AsyncSession, session_id: str) -> None:
        fresh = await project_reader(write, user_id).get_session(project_id)
        if project.files_version != fresh.files_version:
            raise AppError(
                "code_trial_project_changed", "The project has changed. Restart the trial.", 409
            )
        repo = TrialRepository(write, user_id)
        row = await repo.for_version(project_id, fresh.files_version)
        if row is not None:
            if row.pleadings or await _running(write, row):
                raise _AlreadyOpen(row)
            row.session_id = session_id
            return
        selected = python_files(fresh.files)
        if not excerpts(selected):
            raise AppError("code_trial_no_passage", "No Python passage short enough to quote.", 422)
        await repo.add(
            id=trial_id,
            ide_session_id=project_id,
            session_id=session_id,
            title=fresh.title,
            files_version=fresh.files_version,
            snapshot=selected,
        )

    try:
        with inherit_source(user_id, None, "openai"):
            session_id = await launcher.start(
                user_id,
                GRAPH,
                {"trial_id": trial_id},
                subject_type=GRAPH,
                subject_id=trial_id,
                prepare=prepare,
            )
    except _AlreadyOpen as exc:
        return exc.started
    return TrialOpened(trial_id=trial_id, session_id=session_id)


async def read_trial(
    db: AsyncSession, user_id: str, project_id: str, trial_id: str | None = None
) -> TrialView | None:
    project = await project_reader(db, user_id).get_session(project_id)
    repo = TrialRepository(db, user_id)
    row = await repo.require(trial_id) if trial_id is not None else await repo.latest(project_id)
    if row is None:
        return None
    if row.ide_session_id != project_id:
        raise missing()
    return await _view(db, row, project.files_version)


async def save_verdict(
    db: AsyncSession, user_id: str, project_id: str, trial_id: str, verdict: TrialVerdict
) -> TrialView:
    project = await project_reader(db, user_id).get_session(project_id)
    repo = TrialRepository(db, user_id)
    row = await repo.require(trial_id)
    if row.ide_session_id != project_id:
        raise missing()
    if not row.pleadings:
        raise AppError(
            "code_trial_not_ready", "Wait for both pleadings before giving your verdict.", 409
        )
    await repo.set_verdict(row, verdict)
    if _verdict(row) != verdict:
        raise AppError("code_trial_already_decided", "A verdict has already been recorded.", 409)
    return await _view(db, row, project.files_version)
