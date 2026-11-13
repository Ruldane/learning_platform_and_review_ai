"""Port de la replanification (`ReplanStore`, D105) sur les features `replan` et `program` :
implémentation branchée par `bootstrap.agent_ports` (D106). Chaque appel ouvre sa propre session
de base, courte ; les écritures (`preview`, `apply`, `refuse`) passent par
`program.service.replan_versions`, qui prend le verrou du programme avant sa transaction (F4).

Défense en profondeur : le port applique de nouveau les droits de l'option (réduire : retraits
seuls ; approfondir : ajouts seuls ; sinon rien), ignore une référence inconnue (journal : leur
nombre seulement) et ne retire jamais une tâche déjà faite. Le programme d'un autre : 404 à
chaque appel. Journaux : identifiants et nombres seulement (SPEC 17.2)."""

import logging
from collections.abc import Mapping

from app.agents.tools.replan_port import Applied, PreviewSaved, ReplanContext, ReplanDraft
from app.agents.tools.study_schema import ReplanOption, ReplanTrigger
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
    draft: ReplanDraft, refs: Mapping[str, str], option: ReplanOption | None
) -> tuple[set[str], list[NewTask], int]:
    """Retraits (ids des tâches) et ajouts (dans un module connu) que l'option permet, et le
    nombre de références inconnues."""
    drops = draft.drop if option == "reduce_scope" else []
    adds = draft.add if option == "deepen" else []
    drop = {refs[ref] for ref in drops if ref.startswith("t") and ref in refs}
    add = [
        NewTask(refs[t.module], t.title, t.type, t.minutes, str(t.done_criterion))
        for t in adds
        if t.module.startswith("m") and t.module in refs
    ]
    unknown = len(drops) - len(drop) + len(adds) - len(add)
    return drop, add, unknown


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
        drop, add, unknown = _resolved(draft, refs, option)
        if unknown:
            logger.info(
                "Replanification : %d référence(s) inconnue(s) ignorée(s) (session %s)",
                unknown,
                session_id,
            )
        async with self._rt.session_factory() as db:
            today = await self._rt.today(db, user_id)
            facts = await session_facts(db, user_id, session_id)
        entry = facts.input.get("review_entry_id") if facts is not None else None
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
