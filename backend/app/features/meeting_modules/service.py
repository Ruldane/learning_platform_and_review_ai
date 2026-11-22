from hashlib import sha256

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.meeting_modules import MeetingModule
from app.features.meeting_modules.excerpts import extract, study_steps
from app.features.meeting_modules.repository import MeetingModules
from app.features.meeting_modules.schemas import (
    MeetingExcerpt,
    MeetingModuleIn,
    MeetingModuleOut,
    MeetingModuleSummary,
    MeetingSelection,
    MeetingStudyStep,
)

_EXCERPTS = TypeAdapter(list[MeetingExcerpt])
_STEPS = TypeAdapter(list[MeetingStudyStep])


async def require(repo: MeetingModules, module_id: str) -> MeetingModule:
    row = await repo.get(module_id)
    if row is None:
        raise AppError("meeting_module_not_found", "Module introuvable.", 404)
    return row


def view(row: MeetingModule) -> MeetingModuleOut:
    excerpts = _EXCERPTS.validate_python(row.excerpts)
    steps = (
        _STEPS.validate_python(row.module_steps)
        if row.published_at
        else study_steps(excerpts, row.selection)
    )
    return MeetingModuleOut.model_validate(
        {
            "id": row.id,
            "title": row.title,
            "source_digest": row.source_digest,
            "status": "published" if row.published_at else "draft",
            "excerpts": excerpts,
            "selection": row.selection,
            "steps": steps,
            "published_at": row.published_at,
        }
    )


async def read(db: AsyncSession, user_id: str, module_id: str) -> MeetingModuleOut:
    return view(await require(MeetingModules(db, user_id), module_id))


async def history(db: AsyncSession, user_id: str) -> list[MeetingModuleSummary]:
    repo = MeetingModules(db, user_id)
    return [
        MeetingModuleSummary.model_validate(
            {
                "id": row.id,
                "title": row.title,
                "status": "published" if row.published_at else "draft",
                "created_at": row.created_at,
            }
        )
        for row in await repo.recent()
    ]


async def prepare(db: AsyncSession, user_id: str, body: MeetingModuleIn) -> MeetingModuleOut:
    repo = MeetingModules(db, user_id)
    excerpts = extract(body.transcript)
    if not excerpts:
        raise AppError("meeting_transcript_empty", "Ajoute un extrait de réunion exploitable.", 422)
    row = await repo.add(
        title=body.title,
        transcript=body.transcript,
        source_digest=sha256(body.transcript.encode("utf-8")).hexdigest(),
        excerpts=_EXCERPTS.dump_python(excerpts),
    )
    return view(row)


async def choose(
    db: AsyncSession, user_id: str, module_id: str, request: MeetingSelection
) -> MeetingModuleOut:
    repo = MeetingModules(db, user_id)
    await repo.begin_write()
    row = await require(repo, module_id)
    if row.published_at is not None:
        raise AppError("meeting_module_published", "Ce module est déjà rangé.", 409)
    available = {item["line"] for item in row.excerpts}
    if not set(request.lines) <= available:
        raise AppError("meeting_excerpt_unknown", "Une ligne sélectionnée est introuvable.", 422)
    row.selection = list(request.lines)
    return view(row)


async def publish(
    db: AsyncSession, user_id: str, module_id: str, approved: MeetingSelection
) -> MeetingModuleOut:
    repo = MeetingModules(db, user_id)
    await repo.begin_write()
    row = await require(repo, module_id)
    if approved.lines != row.selection:
        raise AppError(
            "meeting_selection_changed", "La sélection a changé. Relis la séquence.", 409
        )
    if row.published_at is not None:
        return view(row)
    if not row.selection:
        raise AppError("meeting_selection_required", "Choisis au moins un extrait.", 409)
    row.module_steps = _STEPS.dump_python(
        study_steps(_EXCERPTS.validate_python(row.excerpts), row.selection)
    )
    row.published_at = utcnow()
    return view(row)
