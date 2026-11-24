"""Ranger l'évaluation d'un rendu (P3, D166) : `AgentProjectStore.save_review`, sous le verrou du
projet, **idempotent par session** (SPEC 9.4) : une évaluation déjà rangée par cette session n'est
pas réécrite, et une évaluation qui n'attend plus (le projet n'est plus `reviewing` pour cette
session : statut corrigé, autre rendu) est ignorée.

Le verdict est recalculé par le code (`verdict`) sur les résultats reçus : « validé » seulement si
chaque critère a un seul résultat atteint **et** que le parcours l'avait jugé validé (un résultat
hors énoncé, écarté du port, ne peut pas faire valider ce que le parcours a jugé à reprendre,
D173). Validé : `validated_at`, les compétences du module
montées à `prouve` avec la preuve `project` (jamais plus bas), une ligne `project` au journal
(`ref_key = project:{id}`) dans la même transaction ; puis, **hors transaction**, le reflet dans les
acquis de la mémoire (auteur `practitioner`), refait au rejeu pour rattraper un arrêt. Les
brouillons ne sont rangés qu'à la validation ; l'entrée de projet n'entre jamais au profil ici.
Journaux : identifiants, nombres et codes."""

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
REFLECT_REASON = "Projet validé : les compétences du module sont prouvées."


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
    """Compétences du module à `prouve`, ligne du journal : dans la transaction de `db`. Rend les
    noms des compétences (à refléter ensuite)."""
    now = rt.now()
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    day = local_today(zone, now)
    names = await module_skills(db, user_id, row)
    label = f"Projet « {row.title} » validé ({day:%d/%m})"
    if names:
        await SkillsService(db, user_id).raise_levels(
            names, "proven", evidence("project", row.id, label, now)
        )
    await add_entry(
        db,
        user_id,
        kind="project",
        text=f"Projet validé : {row.title}",
        occurred_on=day,
        ref_key=f"project:{row.id}",
        links=JournalLinks(session_id=session_id),
        data={"project_id": row.id, "module_id": row.module_id},
    )
    return names


async def _reflect(rt: ProjectsRuntime, user_id: str, session_id: str, names: list[str]) -> None:
    """Le niveau de chaque compétence (qui fait foi) reflété dans les acquis de la mémoire ;
    idempotent, jamais plus bas. Une panne est journalisée (classe seule) : le rejeu la rattrape."""
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
            "Acquis non reflétés après un projet : session %s (%s)", session_id, type(exc).__name__
        )


async def save_review(
    rt: ProjectsRuntime, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
) -> None:
    names: list[str] = []
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        replay = (row.evaluation or {}).get("session_id") == session_id
        if not replay and (row.status != "reviewing" or row.session_id not in (None, session_id)):
            logger.info("Évaluation ignorée : projet %s, session %s", project_id, session_id)
            return
        if not replay:
            evaluation = _evaluation(row, outcome, session_id, rt.now().isoformat())
            row.evaluation, row.status = evaluation, evaluation["verdict"]
            if evaluation["verdict"] == "validated":
                row.validated_at = rt.now()
                row.drafts = {draft.kind: draft_data(draft) for draft in outcome.drafts or []}
                names = await _validate(rt, db, user_id, row, session_id)
            await db.commit()
            logger.info("Évaluation rangée : projet %s, verdict %s", project_id, row.status)
        elif row.status == "validated":
            names = await module_skills(db, user_id, row)
    if names:
        await _reflect(rt, user_id, session_id, names)


async def save_drafts(
    rt: ProjectsRuntime, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
) -> bool:
    """Les brouillons d'un projet **déjà validé** qui n'en a pas (D173 n° 4, D181), sous le verrou
    du projet : la première écriture gagne (un rejeu ou une autre session ne change rien), rien
    n'est rangé si le projet n'est pas validé ou si la liste est vide (« brouillons indisponibles »
    de nouveau). Rend `True` si les brouillons sont rangés, `False` si l'écriture est ignorée.
    L'évaluation, les compétences et le journal ne sont pas touchés."""
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        if row.status != "validated" or row.drafts or not drafts:
            logger.info("Brouillons ignorés : projet %s, session %s", project_id, session_id)
            return False
        row.drafts = {draft.kind: draft_data(draft) for draft in drafts}
        await db.commit()
    logger.info(
        "Brouillons rangés : projet %s, session %s, %d brouillon(s)",
        project_id,
        session_id,
        len(drafts),
    )
    return True
