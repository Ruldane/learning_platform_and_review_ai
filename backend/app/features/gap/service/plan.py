"""« Ajouter au planning » depuis l'écart d'une offre (SPEC F8, D123) : les compétences choisies
doivent être des lignes `to_add` de l'écart recalculé ; elles partent dans une replanification au
déclencheur `gap` du programme validé le plus récent (ajouts seuls, module « Compétences des
offres », proposition soumise à January). Une 422 nomme le rang fautif, jamais sa valeur ; les
journaux ne portent que des identifiants et des nombres (SPEC 17.2)."""

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


def gap_skill_unknown(fields: list[str]) -> AppError:
    return AppError(
        "gap_skill_unknown",
        "Compétence absente des lignes « à ajouter » de l'écart de cette offre.",
        422,
        {"fields": fields},
    )


def no_program() -> AppError:
    return AppError("no_program", "Aucun programme validé : crée d'abord ton programme.", 409)


def chosen_skills(rows: Sequence[GapRow], skills: Sequence[str]) -> list[str]:
    """Les noms des lignes `to_add` demandées (casse, accents et espaces ignorés), une fois
    chacune, dans l'ordre de la demande ; 422 `gap_skill_unknown` (`skills.{rang}`) sinon."""
    to_add = {normalize_skill_name(r.skill): r.skill for r in rows if r.action == "to_add"}
    names: list[str] = []
    fields: list[str] = []
    for index, skill in enumerate(skills):
        name = to_add.get(normalize_skill_name(skill))
        if name is None:
            fields.append(f"skills.{index}")
        elif name not in names:
            names.append(name)
    if fields:
        raise gap_skill_unknown(fields)
    return names


async def plan_gap(rt: ReplanRuntime, user_id: str, posting_id: str, skills: Sequence[str]) -> str:
    """404 `posting_not_found`, 422 `gap_skill_unknown`, 409 `no_program`, puis les refus de
    `start_gap_replan` (409 `replan_open`, `details.session_id`). Rend la session."""
    async with rt.session_factory() as db:
        posting = await get_posting(db, user_id, posting_id)
        names = chosen_skills(await gap_rows(db, user_id, posting), skills)
        program_id = await latest_validated(db, user_id)
    if program_id is None:
        raise no_program()
    session_id = await start_gap_replan(rt, user_id, program_id, names)
    logger.info(
        "Ajout au planning : utilisateur %s, offre %s, programme %s, %d compétence(s), session %s",
        user_id,
        posting_id,
        program_id,
        len(names),
        session_id,
    )
    return session_id
