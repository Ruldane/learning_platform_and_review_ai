"""Le brouillon de veille devient une retouche P11 sur confirmation explicite."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_updates_port import GRAPH
from app.core.errors import AppError
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.lesson_updates import LessonUpdate
from app.features.lesson_updates.repository import UpdatesRepository
from app.features.lesson_updates.schemas import UpdateAccepted, UpdateState, UpdateView
from app.features.lessons.service.direct import submit_revision
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.versions import PublishedVersion, RevisionGuard, published_version
from app.features.sessions.service import session_facts


def _missing() -> AppError:
    return AppError("lesson_update_not_found", "Proposition de mise à jour introuvable.", 404)


async def _owned(db: AsyncSession, user_id: str, lesson_id: str, update_id: str) -> LessonUpdate:
    row = await UpdatesRepository(db, user_id).get(update_id)
    if row is None or row.lesson_id != lesson_id:
        raise _missing()
    return row


async def _state(db: AsyncSession, row: LessonUpdate, lesson: PublishedVersion) -> UpdateState:
    if row.publication_session_id is not None and row.publication_session_id == lesson.session_id:
        return "published"
    if row.base_hash != lesson.digest:
        return "stale"
    if row.publication_session_id is None and row.draft is not None:
        return "ready"
    sid = row.publication_session_id or row.preparation_session_id
    session = await session_facts(db, row.user_id, sid)
    if session is not None and session.status in OPEN_SESSION_STATES:
        return "checking" if row.publication_session_id is not None else "preparing"
    return "failed"


async def list_updates(db: AsyncSession, user_id: str, lesson_id: str) -> list[UpdateView]:
    lesson = await published_version(db, user_id, lesson_id)
    rows = await UpdatesRepository(db, user_id).listed(lesson_id)
    return [
        UpdateView.model_validate(
            {
                "id": row.id,
                "library": row.library,
                "version": row.version,
                "source_url": row.source_url,
                "apis": [item["previous"] for item in row.detected],
                "state": await _state(db, row, lesson),
                "explanation": (row.draft or {}).get("explanation"),
                "changes": (row.draft or {}).get("changes", []),
                "preparation_session_id": row.preparation_session_id,
                "publication_session_id": row.publication_session_id,
            }
        )
        for row in rows
    ]


def _documented(markdown: str, url: str) -> str:
    if url in markdown:
        return markdown
    lines = markdown.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip().casefold().startswith("## auto-évaluation"):
            lines.insert(index, f"- [Journal de versions](<{url}>)\n\n")
            return "".join(lines)
    return markdown


async def _restart_preparation(rt: LessonsRuntime, row: LessonUpdate) -> UpdateAccepted:
    async def attach(db: AsyncSession, session_id: str) -> None:
        claimed = await _owned(db, row.user_id, row.lesson_id, row.id)
        lesson = await published_version(db, row.user_id, row.lesson_id)
        if (
            claimed.preparation_session_id != row.preparation_session_id
            or await _state(db, claimed, lesson) != "failed"
        ):
            raise AppError("lesson_update_changed", "La proposition a changé entre-temps.", 409)
        claimed.preparation_session_id = session_id

    sid = await rt.launcher.start(
        row.user_id,
        GRAPH,
        {"proposal_id": row.id},
        subject_type=GRAPH,
        subject_id=row.id,
        prepare=attach,
    )
    return UpdateAccepted(session_id=sid)


async def accept_update(
    rt: LessonsRuntime, user_id: str, lesson_id: str, update_id: str
) -> UpdateAccepted:
    async with rt.session_factory() as db:
        row = await _owned(db, user_id, lesson_id, update_id)
        published = await published_version(db, user_id, lesson_id)
        state = await _state(db, row, published)
        if state in ("checking", "published") and row.publication_session_id:
            return UpdateAccepted(session_id=row.publication_session_id)
        if state == "preparing":
            return UpdateAccepted(session_id=row.preparation_session_id)
        if state == "stale":
            raise AppError(
                "lesson_update_stale", "La leçon publiée a changé depuis cette proposition.", 409
            )
    if row.draft is None:
        return await _restart_preparation(rt, row)
    markdown = _documented(str(row.draft["markdown"]), row.source_url)
    previous = row.publication_session_id

    async def attach(db: AsyncSession, session_id: str) -> None:
        claimed = await _owned(db, user_id, lesson_id, update_id)
        if claimed.publication_session_id != previous:
            raise AppError("lesson_update_already_sent", "La correction est déjà soumise.", 409)
        claimed.publication_session_id = session_id

    submitted = await submit_revision(
        rt, user_id, lesson_id, markdown, RevisionGuard(row.base_hash, attach)
    )
    if submitted:
        async with rt.session_factory() as db:
            current = await _owned(db, user_id, lesson_id, update_id)
            if current.publication_session_id:
                return UpdateAccepted(session_id=current.publication_session_id)
    raise AppError("lesson_update_conflict", "Une autre retouche est déjà en cours.", 409)
