"""Versions of the targeted CV on the API side (SPEC 5.3, 14.2; D130): list, detail, PDF and
page images. The status follows the outcome of the review's session (`reviews.settle`). The
file name carries January's name: rendered in the download header, never logged."""

from collections.abc import Collection

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.core.errors import AppError
from app.db.models.career import CvVersion
from app.features.cv.repository import ProfileRepository, VersionRepository
from app.features.cv.schemas_reviews import VersionOut
from app.features.cv.service.review_data import version_not_found, version_out
from app.features.cv.service.reviews import settle
from app.features.cv.service.runtime import CvRuntime


def version_not_ready() -> AppError:
    return AppError("version_not_ready", "The PDF is not ready yet.", 404)


def page_not_found() -> AppError:
    return AppError("version_page_not_found", "CV page not found.", 404)


async def list_versions(rt: CvRuntime, user_id: str, posting_id: str | None) -> list[VersionOut]:
    """The versions (of an offer), most recent first."""
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        rows = await VersionRepository(db, user_id).recent(posting_id=posting_id)
        return [version_out(row) for row in rows]


async def _row(rt: CvRuntime, user_id: str, version_id: str) -> CvVersion:
    async with rt.review_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = await VersionRepository(db, user_id).get(version_id)
    if row is None:
        raise version_not_found()
    return row


async def get_version(rt: CvRuntime, user_id: str, version_id: str) -> VersionOut:
    return version_out(await _row(rt, user_id, version_id))


async def version_pdf(rt: CvRuntime, user_id: str, version_id: str) -> tuple[str, bytes]:
    """`(ASCII file name, PDF)`; 404 `version_not_ready` while it is not ready."""
    row = await _row(rt, user_id, version_id)
    if row.status != "ready" or row.storage_key is None:
        raise version_not_ready()
    return row.filename, await rt.storage.read(user_id, row.storage_key)


async def version_page(rt: CvRuntime, user_id: str, version_id: str, number: int) -> bytes:
    """PNG image of page `number` (from 1) of a ready version; 404 otherwise."""
    row = await _row(rt, user_id, version_id)
    if row.status != "ready" or not 1 <= number <= len(row.page_images):
        raise page_not_found()
    return await rt.storage.read(user_id, str(row.page_images[number - 1]))


async def ready_versions_by_posting(db: AsyncSession, user_id: str) -> dict[str, tuple[str, int]]:
    """Read only, for applications: the most recent ready version of each offer,
    `offer → (identifier, number)`. Nothing is set or started: a version still rendering is not
    listed."""
    return await VersionRepository(db, user_id).ready_latest()


async def version_numbers(
    db: AsyncSession, user_id: str, version_ids: Collection[str]
) -> dict[str, int]:
    """Read only, for applications: `version → number` of the given versions."""
    return await VersionRepository(db, user_id).numbers(version_ids)


async def validated_profile(db: AsyncSession, user_id: str) -> MasterProfileData | None:
    """Read only, for applications: the most recent validated master profile, `None` if January
    has not validated one."""
    found = await validated_profile_version(db, user_id)
    return found[1] if found is not None else None


async def validated_profile_version(
    db: AsyncSession, user_id: str
) -> tuple[int, MasterProfileData] | None:
    row = await ProfileRepository(db, user_id).latest("validated")
    return (row.version, MasterProfileData.model_validate(row.data)) if row is not None else None


async def version_ref(db: AsyncSession, user_id: str, version_id: str) -> tuple[str, str] | None:
    """Read only, for the hiring committee: `(offer, status)` of the given version (the user's
    own), `None` if it does not exist."""
    row = await VersionRepository(db, user_id).get(version_id)
    return None if row is None else (row.posting_id, row.status)


async def version_content(db: AsyncSession, user_id: str, version_id: str) -> CvContent | None:
    """Read only, for applications: the CV content of the given version (the user's own), `None`
    if it does not exist or is not readable."""
    row = await VersionRepository(db, user_id).get(version_id)
    if row is None:
        return None
    try:
        return CvContent.model_validate(row.content)
    except ValidationError:
        return None
