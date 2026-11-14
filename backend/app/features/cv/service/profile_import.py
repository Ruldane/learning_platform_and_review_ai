"""Import du profil maître (SPEC 5.1, D124) : le CV (PDF obligatoire) et le profil LinkedIn (PDF
facultatif) sont rangés comme documents de la mémoire, étiquetés `cv` et `linkedin`, puis la
capture `cv_capture` (mode `profile`) part sur ces documents et la note.

Une seule capture du profil à la fois (409 `capture_in_progress`). Un fichier qui n'est pas un PDF
est refusé (415 `unsupported_file_type`), comme un fichier de plus de 10 Mo (413
`file_too_large`) ; aucun message ne cite un nom de fichier ni un contenu (17.2)."""

import logging

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.cv.schemas_profile import ProfileImportStarted
from app.features.cv.service.profile import capture_session
from app.features.cv.service.runtime import CAPTURE_GRAPH, PROFILE_SUBJECT, CvRuntime
from app.features.memory.service.documents import DocumentService
from app.features.memory.service.upload import detect_upload

logger = logging.getLogger(__name__)

MAX_PROFILE_FILE_BYTES = 10 * 1024 * 1024
READ_BLOCK = 1024 * 1024
TOO_LARGE_MESSAGE = "Fichier trop volumineux : 10 Mo au maximum."


def capture_in_progress(session_id: str) -> AppError:
    return AppError(
        "capture_in_progress",
        "Une capture de ton profil est déjà en cours.",
        409,
        {"session_id": session_id},
    )


def pdf_only() -> AppError:
    return AppError(
        "unsupported_file_type", "Type de fichier non pris en charge : PDF uniquement.", 415
    )


def pdf_too_large() -> AppError:
    return AppError("file_too_large", TOO_LARGE_MESSAGE, 413)


async def check_pdf(file: UploadFile) -> None:
    """PDF (extension et contenu) de 10 Mo au plus ; le fichier est rembobiné pour son envoi."""
    blocks: list[bytes] = []
    size = 0
    while block := await file.read(READ_BLOCK):
        size += len(block)
        if size > MAX_PROFILE_FILE_BYTES:
            raise pdf_too_large()
        blocks.append(block)
    try:
        kind = detect_upload(file.filename, b"".join(blocks))
    except AppError:
        raise pdf_only() from None
    if kind != "pdf":
        raise pdf_only()
    await file.seek(0)


async def _store(
    rt: CvRuntime, db: AsyncSession, user_id: str, files: list[tuple[UploadFile, str]]
) -> list[str]:
    """Chaque fichier rangé par l'envoi de la mémoire (doublon : le document existant)."""
    service = DocumentService(db, user_id, rt.memory)
    ids: list[str] = []
    for file, tag in files:
        document, _ = await service.create(file=file, url=None, text=None, title=None, tags=[tag])
        ids.append(document.id)
    return list(dict.fromkeys(ids))


async def start_import(
    rt: CvRuntime,
    db: AsyncSession,
    user_id: str,
    *,
    cv: UploadFile,
    linkedin: UploadFile | None,
    note: str | None,
) -> ProfileImportStarted:
    files = [(cv, "cv")] + ([(linkedin, "linkedin")] if linkedin is not None else [])
    for file, _ in files:
        await check_pdf(file)
    note = note.strip() if note and note.strip() else None
    async with rt.import_lock(user_id):
        if (open_id := await capture_session(db, user_id)) is not None:
            raise capture_in_progress(open_id)
        document_ids = await _store(rt, db, user_id, files)
        await db.commit()  # aucune écriture en attente quand le moteur écrit la session
        body = {"mode": "profile", "document_ids": document_ids, "note": note}
        session_id = await rt.launcher.start(
            user_id, CAPTURE_GRAPH, body, subject_type=PROFILE_SUBJECT, subject_id=user_id
        )
    logger.info(
        "Capture du profil lancée : utilisateur %s, session %s, %d document(s), note %s",
        user_id,
        session_id,
        len(document_ids),
        note is not None,
    )
    return ProfileImportStarted(session_id=session_id, document_ids=document_ids)
