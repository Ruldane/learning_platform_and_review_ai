"""Storing the evaluation of a submission (P3, D166): `AgentProjectStore.save_review`, under the
project's lock, **idempotent per session** (SPEC 9.4): an evaluation already stored by this
session is not rewritten, and an evaluation that is no longer awaited (the project is no longer
`reviewing` for this session: status corrected, another submission) is ignored.

The verdict is recomputed by the code (`verdict`) on the results received: "validated" only if
each criterion has a single met result **and** the flow had judged it validated (a result
outside the statement, discarded by the port, cannot validate what the flow judged to redo,
D173). Validated: `validated_at`, the module's skills raised to `proven` with `project` evidence
(never lower), a `project` line in the log (`ref_key = project:{id}`) in the same transaction;
then, **outside the transaction**, the reflection in the memory's learned items (author
`practitioner`), redone on replay to catch up after a stop. The drafts are only stored at
validation; the project entry never enters the profile here.
Logs: ids, numbers and codes."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.project_port import DraftResult, ReviewOutcome
from app.agents.tools.project_schema import verdict as code_verdict
from app.core.clock import local_today, user_zone
from app.core.skills import evidence
from app.db.models.daily import Project
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.projects.service.inputs import module_skills, owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillLevel, SkillsService

logger = logging.getLogger(__name__)

AUTHOR = "practitioner"
REFLECT_REASON = "Project validated: the module's skills are proven."


def draft_data(draft: DraftResult) -> dict[str, Any]:
    return {
        "status": draft.status,
        "content": draft.content,
        "entry": draft.entry.model_dump(mode="json") if draft.entry else None,
        "flags": list(draft.flags),
        "edited": False,
    }


def _evaluation(
    row: Project, outcome: ReviewOutcome, session_id: str, now_iso: str
) -> dict[str, Any]:
    criteria = len((row.brief or {}).get("criteria", []))
    return {
        "session_id": session_id,
        "at": now_iso,
        "verdict": (
            "validated"
            if outcome.verdict == "validated"
            and code_verdict(criteria, outcome.results) == "validated"
            else "to_redo"
        ),
        "results": [result.model_dump(mode="json") for result in outcome.results],
        "feedback": outcome.feedback,
        "repo_status": outcome.repo_status,
    }


async def _validate(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, row: Project, session_id: str
) -> list[str]:
    """Module skills to `proven`, log line: in the transaction of `db`. Returns the skill names
    (to reflect afterwards)."""
    now = rt.now()
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    day = local_today(zone, now)
    names = await module_skills(db, user_id, row)
    label = f"Project '{row.title}' validated ({day:%d/%m})"
    if names:
        await SkillsService(db, user_id).raise_levels(
            names, "proven", evidence("project", row.id, label, now)
        )
    await add_entry(
        db,
        user_id,
        kind="project",
        text=f"Project validated: {row.title}",
        occurred_on=day,
        ref_key=f"project:{row.id}",
        links=JournalLinks(session_id=session_id),
        data={"project_id": row.id, "module_id": row.module_id},
    )
    return names


async def _reflect(rt: ProjectsRuntime, user_id: str, session_id: str, names: list[str]) -> None:
    """The level of each skill (which is authoritative) reflected in the memory's learned items;
    idempotent, never lower. A failure is logged (class only): the replay catches it up."""
    if not names:
        return
    try:
        async with rt.session_factory() as db:
            levels: list[tuple[str, SkillLevel]] = await SkillsService(db, user_id).levels_of(names)
        await reflect_skill_levels(
            rt.memory, user_id, levels, author=AUTHOR, session_id=session_id, reason=REFLECT_REASON
        )
    except Exception as exc:
        logger.warning(
            "Learned items not reflected after a project: session %s (%s)",
            session_id,
            type(exc).__name__,
        )


async def save_review(
    rt: ProjectsRuntime, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
) -> None:
    names: list[str] = []
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        replay = (row.evaluation or {}).get("session_id") == session_id
        if not replay and (row.status != "reviewing" or row.session_id not in (None, session_id)):
            logger.info("Evaluation ignored: project %s, session %s", project_id, session_id)
            return
        if not replay:
            evaluation = _evaluation(row, outcome, session_id, rt.now().isoformat())
            row.evaluation, row.status = evaluation, evaluation["verdict"]
            if evaluation["verdict"] == "validated":
                row.validated_at = rt.now()
                row.drafts = {draft.kind: draft_data(draft) for draft in outcome.drafts or []}
                names = await _validate(rt, db, user_id, row, session_id)
            await db.commit()
            logger.info("Evaluation stored: project %s, verdict %s", project_id, row.status)
        elif row.status == "validated":
            names = await module_skills(db, user_id, row)
    if names:
        await _reflect(rt, user_id, session_id, names)


async def save_drafts(
    rt: ProjectsRuntime, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
) -> bool:
    """The drafts of an **already validated** project that has none (D173 no. 4, D181), under the
    project's lock: the first write wins (a replay or another session changes nothing), nothing
    is stored if the project is not validated or if the list is empty ("drafts unavailable"
    again). Returns `True` if the drafts are stored, `False` if the write is ignored. The
    evaluation, the skills and the log are not touched."""
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        if row.status != "validated" or row.drafts or not drafts:
            logger.info("Drafts ignored: project %s, session %s", project_id, session_id)
            return False
        row.drafts = {draft.kind: draft_data(draft) for draft in drafts}
        await db.commit()
    logger.info(
        "Drafts stored: project %s, session %s, %d draft(s)",
        project_id,
        session_id,
        len(drafts),
    )
    return True
