"""Infers actual usages and reserves an independent proposal for each mirror."""

from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.lesson_updates_port import GRAPH
from app.core.errors import AppError
from app.features.ledger.service.ledger import scheduled_user_ids
from app.features.lesson_updates.impact import examples_in
from app.features.lesson_updates.release_notes import ApiChange, Release, changes_in
from app.features.lesson_updates.repository import UpdatesRepository
from app.features.lessons.service.production import ProductionContext
from app.features.lessons.service.versions import (
    PublishedVersion,
    published_version,
    update_targets,
)
from app.features.reading_stack.service.releases import collected_releases

MAX_PER_PASS = 12


class _AlreadySeen(Exception):
    pass


async def _launch(
    rt: ProductionContext,
    user_id: str,
    lesson: PublishedVersion,
    release: Release,
    detected: list[ApiChange],
) -> bool:
    key = f"{user_id}/{lesson.id}/{release.library}/{release.version}"
    proposal_id = str(uuid5(NAMESPACE_URL, f"tremplin/lesson-update/{key}"))

    async def prepare(db: AsyncSession, session_id: str) -> None:
        repo = UpdatesRepository(db, user_id)
        current = await published_version(db, user_id, lesson.id)
        if current.digest != lesson.digest:
            raise _AlreadySeen()
        exists = await repo.get(proposal_id)
        fields = {
            "source_url": release.url,
            "base_hash": lesson.digest,
            "detected": [asdict(change) for change in detected],
            "preparation_session_id": session_id,
        }
        if exists is not None:
            if exists.publication_session_id or exists.base_hash == lesson.digest:
                raise _AlreadySeen()
            await repo.update(proposal_id, draft=None, **fields)
            return
        await repo.add(
            id=proposal_id,
            lesson_id=lesson.id,
            library=release.library,
            version=release.version,
            **fields,
        )

    try:
        await rt.launcher.start(
            user_id,
            GRAPH,
            {"proposal_id": proposal_id},
            subject_type=GRAPH,
            subject_id=proposal_id,
            prepare=prepare,
        )
    except _AlreadySeen:
        return False
    return True


async def scan_user(rt: ProductionContext, user_id: str) -> int:
    async with rt.session_factory() as db:
        incoming = await collected_releases(db, user_id)
        releases = [
            release
            for source in incoming
            for release in changes_in(source.title, source.text, source.url)
        ]
        if not releases:
            return 0
        targets = await update_targets(
            db, user_id, list(dict.fromkeys(r.library for r in releases))
        )
        known = await UpdatesRepository(db, user_id).known_versions()
    opened = 0
    for lesson in targets:
        used = set().union(*(block.symbols for block in examples_in(lesson.markdown)))
        if not used:
            continue
        for release in releases:
            key = (lesson.id, release.library, release.version)
            if key in known and known[key] in (None, lesson.digest):
                continue
            detected = [change for change in release.changes if change.previous in used]
            if detected and await _launch(rt, user_id, lesson, release, detected):
                known[key] = lesson.digest
                opened += 1
                if opened >= MAX_PER_PASS:
                    return opened
    return opened


async def scan_all(rt: ProductionContext) -> None:
    async with rt.session_factory() as db:
        users = await scheduled_user_ids(db)
    for user_id in users:
        try:
            await scan_user(rt, user_id)
        except AppError:
            # A program being deleted will be reread on the next pass.
            continue
