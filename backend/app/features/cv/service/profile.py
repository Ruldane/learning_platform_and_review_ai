"""January's master profile (SPEC 5.1, D124): state (validated version, more recent draft,
capture in progress), versions, and validation by January.

Validating creates a `validated` version (source `january`): never an overwrite, the ids of the
kept facts (`keep_known`), the profile's skills raised to `declared` at least with a `cv`
proof (never lowered), then reflected in the memory's learned items outside the lock (D6).
Logs: ids and numbers only (17.2)."""

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

EVIDENCE_LABEL = "Master profile"
REFLECT_REASON = "Master profile validated: January declares these skills."


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
    """The profile capture still open, `None` otherwise."""
    return await find_active_session(
        db, user_id, graph=CAPTURE_GRAPH, subject_type=PROFILE_SUBJECT, subject_id=user_id
    )


async def source_document_id(db: AsyncSession, user_id: str) -> str | None:
    """The CV of the last profile import (`document_ids` of the Archivist's drafts, CV first):
    the document labelled `cv` that still exists, otherwise `None`."""
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
    """The new version and the current level of its skills (to reflect in memory)."""
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
    changed = await skills.raise_levels(names, "declared", proof)
    logger.info(
        "Profile validated: user %s, profile %s, version %d, %d skill(s), %d level(s) raised",
        user_id,
        row.id,
        row.version,
        len(names),
        len(changed),
    )
    return row, await skills.levels_of(names)


async def _reflect(rt: CvRuntime, user_id: str, levels: list[tuple[str, SkillLevel]]) -> None:
    """Reflects the levels in the learned items (D6), OUTSIDE the lock: vectorizing a created
    item calls the embeddings provider. Idempotent; a failure is logged (type only) and caught
    up by the next validation."""
    try:
        await reflect_skill_levels(
            rt.memory, user_id, levels, author="user", session_id=None, reason=REFLECT_REASON
        )
    except Exception as exc:
        logger.warning(
            "Learned items not reflected after profile validation: user %s (%s)",
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
    """New validated version; 409 `profile_conflict` if `base_version` is not the latest (or if
    another version was written meanwhile). `in_transaction(db, version)`: a write by another
    feature in the **same transaction** as the version (all or nothing)."""
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
    """New validated version of `data`; returns its number. For the other features (the entry
    of a validated project, D166), which never import the CV schemas (contract 2). Same 409s as
    `save_profile`."""
    body = ProfilePutIn(data=data, base_version=base_version)
    saved = await save_profile(rt, user_id, body, in_transaction=in_transaction)
    return saved.version
