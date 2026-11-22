"""« Ajouter au planning » depuis l'écart d'une offre (SPEC F8, D123) : les lignes cochées
alimentent une proposition de replanification pour le programme validé choisi, avec le plus récent
par défaut. Une 422 donne le rang fautif, et les journaux gardent identifiants et nombres."""

import logging
from collections.abc import Sequence

from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.features.gap.service.rows import gap_rows
from app.features.gap.service.score import GapRow
from app.features.postings.service.queries import get_posting
from app.features.program.service.replan_gap import latest_validated
from app.features.replan.service.launch import start_gap_replan
from app.features.replan.service.runtime import ReplanRuntime

logger = logging.getLogger(__name__)


def gap_skill_unknown(fields: list[str], *, allow_out_of_scope: bool) -> AppError:
    lines = "« à ajouter » ou « hors périmètre »" if allow_out_of_scope else "« à ajouter »"
    return AppError(
        "gap_skill_unknown",
        f"Compétence absente des lignes {lines} de l'écart de cette offre.",
        422,
        {"fields": fields},
    )


def no_program() -> AppError:
    return AppError("no_program", "Aucun programme validé : crée d'abord ton programme.", 409)


def chosen_skills(
    rows: Sequence[GapRow], skills: Sequence[str], *, allow_out_of_scope: bool = False
) -> list[str]:
    """Renvoie les noms canoniques des lignes cochées, sans doublon, dans l'ordre de la demande."""
    allowed = {"to_add", "out_of_scope"} if allow_out_of_scope else {"to_add"}
    to_add = {normalize_skill_name(r.skill): r.skill for r in rows if r.action in allowed}
    names: list[str] = []
    fields: list[str] = []
    for index, skill in enumerate(skills):
        name = to_add.get(normalize_skill_name(skill))
        if name is None:
            fields.append(f"skills.{index}")
        elif name not in names:
            names.append(name)
    if fields:
        raise gap_skill_unknown(fields, allow_out_of_scope=allow_out_of_scope)
    return names


async def plan_gap(
    rt: ReplanRuntime,
    user_id: str,
    posting_id: str,
    skills: Sequence[str],
    *,
    program_id: str | None = None,
) -> str:
    """Lance une proposition dans un programme validé appartenant à l'utilisatrice."""
    async with rt.session_factory() as db:
        posting = await get_posting(db, user_id, posting_id)
        names = chosen_skills(await gap_rows(db, user_id, posting), skills, allow_out_of_scope=True)
        target = program_id if program_id is not None else await latest_validated(db, user_id)
    if target is None:
        raise no_program()
    session_id = await start_gap_replan(rt, user_id, target, names)
    logger.info(
        "Ajout au planning : utilisateur %s, offre %s, programme %s, %d compétence(s), session %s",
        user_id,
        posting_id,
        target,
        len(names),
        session_id,
    )
    return session_id
