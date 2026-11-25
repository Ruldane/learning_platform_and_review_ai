"""Replanning port (`ReplanStore`, D105) over the `replan` and `program` features:
implementation wired by `bootstrap.agent_ports` (D106). Each call opens its own short database
session; writes (`preview`, `apply`, `refuse`) go through `program.service.replan_versions`,
which takes the program lock before its transaction (F4).

Defence in depth: the port enforces the option's rights again (reduce: removals only; deepen:
additions only; otherwise nothing; the session's `gap` trigger, D123: additions only, in `m0`,
that name one of the session's skills), ignores an unknown reference (log: their count only)
and never removes a task already done. Someone else's program: 404 on every call. Logs:
identifiers and counts only (SPEC 17.2)."""

import logging
from collections.abc import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.replan_port import (
    GAP_MODULE_REF,
    Applied,
    PreviewSaved,
    ReplanContext,
    ReplanDraft,
    skills_named,
)
from app.agents.tools.study_schema import ReplanOption, ReplanReading, ReplanTrigger
from app.core.clock import local_today
from app.features.calendar.service.availability import day_caps
from app.features.program.service.programs import load
from app.features.program.service.replan_rows import NewTask
from app.features.program.service.replan_versions import (
    Proposal,
    apply_version,
    refuse_version,
    save_proposal,
)
from app.features.replan.service.context import build_context
from app.features.replan.service.runtime import ReplanRuntime
from app.features.sessions.service import session_facts

logger = logging.getLogger(__name__)


def _resolved(
    draft: ReplanDraft, refs: Mapping[str, str], option: ReplanOption | None, skills: list[str]
) -> tuple[set[str], list[NewTask], list[str], int]:
    """Removals (task ids) and additions (in a known module) that the option allows, the skills
    named by the additions, and the number of unknown references or ignored proposals. `gap`
    trigger (`skills`, D123): additions only, all in `m0`, and only those that name one of the
    session's skills."""
    drops = draft.drop if option == "reduce_scope" and not skills else []
    adds = draft.add if option == "deepen" or skills else []
    named: list[str] = []
    if skills:
        found = [(task, skills_named(task, skills)) for task in adds]
        adds = [t.model_copy(update={"module": GAP_MODULE_REF}) for t, names in found if names]
        named = [skill for skill in skills if any(skill in names for _, names in found)]
    drop = {refs[ref] for ref in drops if ref.startswith("t") and ref in refs}
    add = [
        NewTask(refs[t.module], t.title, t.type, t.minutes, str(t.done_criterion))
        for t in adds
        if t.module.startswith("m") and t.module in refs
    ]
    if skills:
        return drop, add, named, len(draft.drop) + len(draft.add) - len(add)
    return drop, add, named, len(drops) - len(drop) + len(adds) - len(add)


def _gap_skills(facts_input: Mapping[str, object]) -> list[str]:
    """The skills of a session with the `gap` trigger (empty otherwise)."""
    raw = facts_input.get("skills")
    if facts_input.get("trigger") != "gap" or not isinstance(raw, list):
        return []
    return [str(skill) for skill in raw]


async def _reading_additions(
    db: AsyncSession, user_id: str, program_id: str, reading: ReplanReading
) -> list[NewTask]:
    loaded = await load(db, user_id, program_id)
    active = {module.id for module in loaded.modules if not module.skipped}
    task = min(
        (task for task in loaded.tasks if task.status == "todo" and task.module_id in active),
        key=lambda task: task.planned_date,
        default=None,
    )
    if task is None:
        return []
    return [
        NewTask(task.module_id, f"Read: {reading.title}"[:200], "read", 15, f"Read {reading.url}")
    ]


class AgentReplanStore:
    def __init__(self, runtime: ReplanRuntime) -> None:
        self._rt = runtime

    async def context(
        self,
        user_id: str,
        program_id: str,
        *,
        trigger: ReplanTrigger,
        review_entry_id: str | None,
        available_minutes: int | None,
        message: str | None,
        skills: Sequence[str] = (),
    ) -> ReplanContext:
        async with self._rt.session_factory() as db:
            return await build_context(
                db,
                user_id,
                program_id,
                today=await self._rt.today(db, user_id),
                trigger=trigger,
                review_entry_id=review_entry_id,
                available_minutes=available_minutes,
                message=message,
                skills=skills,
            )

    async def preview(
        self,
        user_id: str,
        session_id: str,
        program_id: str,
        draft: ReplanDraft,
        *,
        refs: Mapping[str, str],
        option: ReplanOption | None,
        revision: int,
        reason: str,
        week_cap_override: int | None,
    ) -> PreviewSaved:
        now = self._rt.now()
        async with self._rt.session_factory() as db:
            zone = await self._rt.zone(db, user_id)
            facts = await session_facts(db, user_id, session_id)
            given = facts.input if facts is not None else {}
            if given.get("trigger") == "reading":
                reading = ReplanReading.model_validate(given.get("reading"))
                add = await _reading_additions(db, user_id, program_id, reading)
                drop, named, unknown = set[str](), list[str](), 0
                reason = "Reading chosen from the reading stack"
            else:
                drop, add, named, unknown = _resolved(draft, refs, option, _gap_skills(given))
        today = local_today(zone, now)
        calendar = self._rt.calendar
        caps = await day_caps(calendar, user_id, today, zone, now) if calendar else {}
        if unknown:
            logger.info(
                "Replanning: %d unknown reference(s) or out-of-rights proposal(s) "
                "ignored (session %s)",
                unknown,
                session_id,
            )
        entry = given.get("review_entry_id")
        proposal = Proposal(
            session_id=session_id,
            revision=revision,
            reason=reason,
            drop=drop,
            add=add,
            option=option,
            week_cap_override=week_cap_override,
            review_entry_id=entry if isinstance(entry, str) else None,
            today=today,
            skills=named,
            daily_caps=caps,
        )
        return await save_proposal(self._rt.program, user_id, program_id, proposal)

    async def apply(self, user_id: str, session_id: str, program_id: str, version: int) -> Applied:
        async with self._rt.session_factory() as db:
            today = await self._rt.today(db, user_id)
        return await apply_version(
            self._rt.program, user_id, program_id, version, self._rt.now(), today
        )

    async def refuse(self, user_id: str, session_id: str, program_id: str, version: int) -> None:
        await refuse_version(self._rt.program, user_id, program_id, version)
