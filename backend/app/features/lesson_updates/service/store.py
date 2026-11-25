"""The Verifier can only prepare blocks whose usage has been observed."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.lesson_updates_port import SuggestedRevision
from app.core.errors import AppError
from app.db.models.lesson_updates import LessonUpdate
from app.features.lesson_updates.impact import (
    Example,
    examples_in,
    python_symbols,
    replace_examples,
)
from app.features.lesson_updates.repository import UpdatesRepository
from app.features.lessons.service.versions import PublishedVersion, published_version


def _stale() -> AppError:
    return AppError(
        "lesson_update_stale", "The published lesson has changed since this proposal.", 409
    )


async def _bound(
    db: AsyncSession, user_id: str, session_id: str, proposal_id: str
) -> tuple[LessonUpdate, PublishedVersion]:
    row = await UpdatesRepository(db, user_id).get(proposal_id)
    if row is None or row.preparation_session_id != session_id:
        raise AppError("lesson_update_not_found", "Update proposal not found.", 404)
    lesson = await published_version(db, user_id, row.lesson_id)
    if lesson.digest != row.base_hash:
        raise _stale()
    return row, lesson


def _affected(row: LessonUpdate, lesson: PublishedVersion) -> tuple[dict[str, str], list[Example]]:
    expected = {str(change["previous"]): str(change["replacement"]) for change in row.detected}
    examples = [
        example for example in examples_in(lesson.markdown) if example.symbols & expected.keys()
    ]
    return expected, examples


def _invalid() -> AppError:
    return AppError(
        "lesson_update_ungrounded", "The correction does not apply the documented changes.", 502
    )


def _revision(
    row: LessonUpdate, lesson: PublishedVersion, result: SuggestedRevision
) -> dict[str, object]:
    expected, examples = _affected(row, lesson)
    replacements = {item.block: item.code.rstrip() for item in result.replacements}
    if set(replacements) != {example.block for example in examples} or len(replacements) != len(
        result.replacements
    ):
        raise _invalid()
    for example in examples:
        changed = replacements[example.block]
        if any(line.lstrip().startswith(("```", "~~~")) for line in changed.splitlines()):
            raise _invalid()
        symbols = python_symbols(changed)
        affected = example.symbols & expected.keys()
        if symbols & affected or not {expected[api] for api in affected} <= symbols:
            raise _invalid()
    markdown = replace_examples(lesson.markdown, examples, replacements)
    return {
        "explanation": result.explanation,
        "markdown": markdown,
        "changes": [
            {"block": example.block, "before": example.code, "after": replacements[example.block]}
            for example in examples
        ],
    }


class AgentLessonUpdatesStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(
        self, user_id: str, session_id: str, proposal_id: str
    ) -> dict[str, object] | None:
        async with self._factory() as db:
            row, lesson = await _bound(db, user_id, session_id, proposal_id)
            if row.draft is not None:
                return None
            _, affected = _affected(row, lesson)
            if not affected or len(affected) > 8:
                raise _invalid()
            return {
                "library": row.library,
                "version": row.version,
                "source_url": row.source_url,
                "changelog": row.detected,
                "examples": [
                    {"block": example.block, "code": example.code} for example in affected
                ],
            }

    async def prepare(
        self, user_id: str, session_id: str, proposal_id: str, revision: SuggestedRevision
    ) -> None:
        async with self._factory() as db:
            row, lesson = await _bound(db, user_id, session_id, proposal_id)
            if row.draft is None:
                draft = _revision(row, lesson, revision)
                if not await UpdatesRepository(db, user_id).save_draft(
                    proposal_id, session_id, draft
                ):
                    raise _stale()
                await db.commit()
