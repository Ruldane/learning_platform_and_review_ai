"""Références d'explication liées à une version en lecture seule."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import Caller
from app.core.errors import AppError
from app.features.conversations.feynman_schemas import FeynmanData, FeynmanSource
from app.features.conversations.lesson_context import lesson_material, lesson_version
from app.features.ide.service import IdeService
from app.features.lessons.service.lessons import get_lesson
from app.features.program.service.programs import load


async def lesson_source(db: AsyncSession, user: str, lesson_id: str) -> tuple[FeynmanData, str]:
    lesson = await get_lesson(db, user, lesson_id)
    if lesson.status != "ready":
        raise AppError("lesson_not_ready", "Cette leçon n'est pas encore prête.", 409)
    program = await load(db, user, lesson.program_id)
    module = next((m for m in program.modules if m.id == lesson.module_id), None)
    skill = next((str(s) for s in module.skills if str(s).strip()), None) if module else None
    data = FeynmanData.model_validate(
        {
            "source": {"kind": "lesson", "id": lesson_id, "title": lesson.title},
            "skill": skill,
            "module_id": lesson.module_id,
        }
    )
    return data, lesson.markdown


async def file_source(
    db: AsyncSession, user: str, session_id: str, path: str | None
) -> tuple[FeynmanData, str]:
    ide = IdeService(db, user, None, Caller("app", "feynman"))
    project = await ide.get_session(session_id)
    file = path if path is not None else project.entry
    if file not in project.files:
        raise AppError("feynman_file_not_found", "Fichier enregistré introuvable.", 404)
    skill = "Développement Python" if file.lower().endswith((".py", ".ipynb")) else None
    data = FeynmanData.model_validate(
        {
            "source": {"kind": "ide", "id": session_id, "title": project.title, "path": file},
            "skill": skill,
        }
    )
    return data, project.files[file]


async def material(db: AsyncSession, user: str, source: FeynmanSource, version: str | None) -> str:
    target = str(source.id)
    if source.kind == "lesson":
        _, raw = await lesson_source(db, user, target)
    else:
        _, raw = await file_source(db, user, target, source.path)
    if lesson_version(raw) != version:
        raise AppError(
            "feynman_source_changed", "La source a changé. Commence une nouvelle explication.", 409
        )
    return lesson_material(raw, None, None) if source.kind == "lesson" else raw
