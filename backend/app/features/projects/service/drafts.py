"""Retoucher un brouillon (rule 4, D166) : `PATCH /projects/{id}/drafts/{kind}`, sous le verrou du
projet. Le texte de January remplace celui du brouillon (`edited = true`) : `content` pour la
ligne de CV, le post LinkedIn et le plan du README ; `entry` pour l'entrée de projet (dont le
contenu devient son texte, comme `draft_text`). Un brouillon `to_check` modifié est recontrôlé
par `text_claims` contre **la même référence** que le Praticien (profil validé, ce que January dit
de son projet, compétences du module, titre de l'énoncé autorisé) et, pour le post LinkedIn, la
longueur de 80 à 200 mots : `flags` est mis à jour, le brouillon est `ready` s'il est vide. Un
brouillon `ready` retouché reste `ready` : ce sont ses mots. Rien n'entre au profil maître ici.
422 sans écho (`fields`) si le champ n'est pas celui du type. Journaux : identifiants seulement."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.project_schema import (
    LINKEDIN_WORDS,
    DraftKind,
    linkedin_words,
    project_fact,
    project_reference,
)
from app.agents.tools.text_claims import text_claims
from app.db.models.daily import Project
from app.features.cv.service.versions import validated_profile
from app.features.projects.schemas import DraftPatchIn, ProfileEntryIn, ProjectOut
from app.features.projects.service.errors import draft_not_found, invalid_submission
from app.features.projects.service.inputs import latest_submission, module_skills, owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import project_out_live

logger = logging.getLogger(__name__)


def entry_text(entry: ProfileEntryIn) -> str:
    """Le texte de l'entrée de projet que `text_claims` contrôle (comme `draft_text`)."""
    return "\n".join([entry.name, entry.description, *entry.achievements]).strip()


def _new_content(kind: DraftKind, body: DraftPatchIn) -> tuple[str, ProfileEntryIn | None]:
    """Le texte et l'entrée retouchés ; 422 (`entry` ou `content`) si le champ ne va pas au type."""
    if kind == "profile_entry":
        if body.entry is None or body.content is not None:
            raise invalid_submission(["entry"])
        return entry_text(body.entry), body.entry
    text = (body.content or "").strip()
    if not text or body.entry is not None:
        raise invalid_submission(["content" if body.entry is None else "entry"])
    return text, None


async def _flags(
    db: AsyncSession, user_id: str, row: Project, kind: DraftKind, text: str
) -> list[str]:
    """Les termes que la référence ne dit pas, puis la longueur du post LinkedIn hors bornes."""
    submission = latest_submission(row)
    skills = await module_skills(db, user_id, row)
    title = str((row.brief or {}).get("title", row.title))
    fact = project_fact(title, submission.get("description"), skills, submission.get("repo_url"))
    reference = project_reference(await validated_profile(db, user_id), fact, skills)
    claims = text_claims(text, reference, allowed=[title])
    flags = list(dict.fromkeys(claim.term for claim in claims))
    low, high = LINKEDIN_WORDS
    words = linkedin_words(text)
    if kind == "linkedin_post" and not low <= words <= high:
        flags.append(f"{words} mots ({low} à {high} attendus)")
    return flags


async def patch_draft(
    rt: ProjectsRuntime, user_id: str, project_id: str, kind: DraftKind, body: DraftPatchIn
) -> ProjectOut:
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        item = (row.drafts or {}).get(kind)
        if not item:
            raise draft_not_found()
        text, entry = _new_content(kind, body)
        new = {
            **item,
            "content": text,
            "entry": entry.model_dump(mode="json") if entry else None,
            "edited": True,
        }
        if item.get("status") == "to_check":
            flags = await _flags(db, user_id, row, kind, text)
            new["flags"], new["status"] = flags, "to_check" if flags else "ready"
        row.drafts = {**row.drafts, kind: new}
        await db.commit()
        logger.info(
            "Brouillon retouché : projet %s, type %s, statut %s", project_id, kind, new["status"]
        )
        return await project_out_live(db, user_id, row)
