"""Versions du CV ciblé côté API (SPEC 5.3, 14.2 ; D130) : liste, détail, PDF et images des
pages. Le statut suit l'issue de la session de la revue (`reviews.settle`). Le nom du fichier
porte le nom de January : rendu dans l'en-tête de téléchargement, jamais journalisé."""

from app.core.errors import AppError
from app.db.models.career import CvVersion
from app.features.cv.repository import VersionRepository
from app.features.cv.schemas_reviews import VersionOut
from app.features.cv.service.review_data import version_not_found, version_out
from app.features.cv.service.reviews import settle
from app.features.cv.service.runtime import CvRuntime


def version_not_ready() -> AppError:
    return AppError("version_not_ready", "Ce PDF n'est pas prêt.", 404)


def page_not_found() -> AppError:
    return AppError("version_page_not_found", "Page du CV introuvable.", 404)


async def list_versions(rt: CvRuntime, user_id: str, posting_id: str | None) -> list[VersionOut]:
    """Les versions (d'une offre), la plus récente d'abord."""
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
    """`(nom ASCII du fichier, PDF)` ; 404 `version_not_ready` tant qu'il n'est pas prêt."""
    row = await _row(rt, user_id, version_id)
    if row.status != "ready" or row.storage_key is None:
        raise version_not_ready()
    return row.filename, await rt.storage.read(user_id, row.storage_key)


async def version_page(rt: CvRuntime, user_id: str, version_id: str, number: int) -> bytes:
    """Image PNG de la page `number` (depuis 1) d'une version prête ; 404 sinon."""
    row = await _row(rt, user_id, version_id)
    if row.status != "ready" or not 1 <= number <= len(row.page_images):
        raise page_not_found()
    return await rt.storage.read(user_id, str(row.page_images[number - 1]))
