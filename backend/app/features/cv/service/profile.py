"""Le profil maître de January (SPEC 5.1, D124) : état (version validée, brouillon plus récent,
capture en cours), versions, et validation par January.

Valider crée une version `validated` (source `january`) : jamais d'écrasement, les ids des faits
gardés (`keep_known`), les compétences du profil montées à `declare` au moins avec une preuve
`cv` (jamais de baisse), puis reflétées dans les acquis de la mémoire hors du verrou (D6).
Journaux : identifiants et nombres seulement (17.2)."""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import MasterProfileData
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.models.career import MasterProfile
from app.features.cv.repository import ProfileRepository
from app.features.cv.schemas_profile import (
    ProfileOut,
    ProfilePutIn,
    ProfileStateOut,
    ProfileVersionOut,
)
from app.features.cv.service.profile_merge import all_ids, keep_known
from app.features.cv.service.runtime import CAPTURE_GRAPH, PROFILE_SUBJECT, CvRuntime
from app.features.memory.service.document_files import document_tags
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.sessions.service import find_active_session
from app.features.skills.service import SkillLevel, SkillsService

logger = logging.getLogger(__name__)

EVIDENCE_LABEL = "Profil maître"
REFLECT_REASON = "Profil maître validé : January déclare ces compétences."


def profile_conflict() -> AppError:
    return AppError(
        "profile_conflict",
        "Your profile has changed. Reload it before saving.",
        409,
    )


def to_profile_out(row: MasterProfile) -> ProfileOut:
    return ProfileOut.model_validate(
        {
            "version": row.version,
            "status": row.status,
            "data": row.data,
            "source": row.source,
            "created_at": row.created_at,
            "dropped": [str(line) for line in row.dropped],
        }
    )


async def capture_session(db: AsyncSession, user_id: str) -> str | None:
    """La capture du profil encore ouverte, `None` sinon."""
    return await find_active_session(
        db, user_id, graph=CAPTURE_GRAPH, subject_type=PROFILE_SUBJECT, subject_id=user_id
    )


async def source_document_id(db: AsyncSession, user_id: str) -> str | None:
    """Le CV du dernier import du profil (`document_ids` des brouillons de l'Archiviste, CV
    d'abord) : le document étiqueté `cv` qui existe encore, sinon `None`."""
    for row in await ProfileRepository(db, user_id).all_versions():
        for document_id in map(str, row.document_ids):
            if "cv" in (await document_tags(db, user_id, document_id) or ()):
                return document_id
    return None


async def profile_state(db: AsyncSession, user_id: str) -> ProfileStateOut:
    repo = ProfileRepository(db, user_id)
    validated = await repo.latest("validated")
    draft = await repo.latest("draft")
    if draft is not None and validated is not None and draft.version < validated.version:
        draft = None
    return ProfileStateOut(
        validated=to_profile_out(validated) if validated else None,
        draft=to_profile_out(draft) if draft else None,
        session_id=await capture_session(db, user_id),
        source_document_id=await source_document_id(db, user_id),
    )


async def profile_versions(db: AsyncSession, user_id: str) -> list[ProfileVersionOut]:
    rows = await ProfileRepository(db, user_id).all_versions()
    return [
        ProfileVersionOut(
            version=row.version,
            status=row.status,  # type: ignore[arg-type]  # colonne texte, valeurs de ProfileStatus
            source=row.source,  # type: ignore[arg-type]  # colonne texte, valeurs de ProfileOrigin
            created_at=row.created_at,
        )
        for row in rows
    ]


async def _write(
    rt: CvRuntime, db: AsyncSession, user_id: str, body: ProfilePutIn
) -> tuple[MasterProfile, list[tuple[str, SkillLevel]]]:
    """La nouvelle version et le niveau actuel de ses compétences (à refléter en mémoire)."""
    repo = ProfileRepository(db, user_id)
    rows = await repo.all_versions()
    top = rows[0].version if rows else None
    if body.base_version != top:
        raise profile_conflict()
    taken = all_ids(MasterProfileData.model_validate(row.data) for row in rows)
    data = keep_known(body.data, taken)
    row = await repo.add(
        version=(top or 0) + 1,
        status="validated",
        data=data.model_dump(mode="json"),
        source="january",
        dropped=[],
    )
    names = [skill.name for skill in data.skills]
    proof = evidence("cv", row.id, EVIDENCE_LABEL, rt.now())
    skills = SkillsService(db, user_id)
    changed = await skills.raise_levels(names, "declare", proof)
    logger.info(
        "Profil validé : utilisateur %s, profil %s, version %d, %d compétence(s), %d niveau(x) "
        "monté(s)",
        user_id,
        row.id,
        row.version,
        len(names),
        len(changed),
    )
    return row, await skills.levels_of(names)


async def _reflect(rt: CvRuntime, user_id: str, levels: list[tuple[str, SkillLevel]]) -> None:
    """Reflète les niveaux dans les acquis (D6), HORS du verrou : la vectorisation d'un acquis
    créé appelle le fournisseur d'embeddings. Idempotent ; une panne est journalisée (type seul)
    et rattrapée par la validation suivante."""
    try:
        await reflect_skill_levels(
            rt.memory, user_id, levels, author="user", session_id=None, reason=REFLECT_REASON
        )
    except Exception as exc:
        logger.warning(
            "Acquis non reflétés après validation du profil : utilisateur %s (%s)",
            user_id,
            type(exc).__name__,
        )


async def save_profile(
    rt: CvRuntime,
    user_id: str,
    body: ProfilePutIn,
    *,
    in_transaction: Callable[[AsyncSession, int], Awaitable[None]] | None = None,
) -> ProfileOut:
    """Nouvelle version validée ; 409 `profile_conflict` si `base_version` n'est pas la dernière
    (ou si une autre version a été écrite pendant ce temps). `in_transaction(db, version)` : une
    écriture d'une autre feature dans la **même transaction** que la version (tout ou rien)."""
    async with rt.version_lock(user_id), rt.session_factory() as db:
        row, levels = await _write(rt, db, user_id, body)
        if in_transaction is not None:
            await in_transaction(db, row.version)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise profile_conflict() from None
        out = to_profile_out(row)
    await _reflect(rt, user_id, levels)
    return out


async def save_profile_data(
    rt: CvRuntime,
    user_id: str,
    data: MasterProfileData,
    base_version: int | None,
    *,
    in_transaction: Callable[[AsyncSession, int], Awaitable[None]] | None = None,
) -> int:
    """Nouvelle version validée de `data` ; rend son numéro. Pour les autres features (l'entrée
    d'un projet validé, D166), qui n'importent jamais les schémas du CV (contrat 2). Mêmes 409
    que `save_profile`."""
    body = ProfilePutIn(data=data, base_version=base_version)
    saved = await save_profile(rt, user_id, body, in_transaction=in_transaction)
    return saved.version
