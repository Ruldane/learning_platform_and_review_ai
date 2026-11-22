"""Les opérations d'arborescence conservent l'entrée, la version et le compte."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import Caller
from app.core.errors import AppError
from app.features.ide.service import project_files, sessions
from app.features.ide.service.context import IdeContext
from app.providers.sandbox.base import MAX_FILES, MAX_TOTAL_BYTES

OWNER = "projet-a"


def _context(db: AsyncSession, user: str = OWNER) -> IdeContext:
    return IdeContext(db, user, None, Caller("app", "app"))


async def test_files_can_be_added_renamed_and_removed_and_the_entry_follows(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with db_session_factory() as db:
        ctx = _context(db)
        started = await sessions.open_session(ctx, None, "Projet exemple")
        sid = started.id
        file = await project_files.create(ctx, sid, "src/util.py", "x = 1\n", version=0)
        assert file.files_version == 1 and file.files["src/util.py"] == "x = 1\n"
        renamed = await project_files.rename(ctx, sid, "main.py", "src/main.py", version=1)
        assert renamed.files_version == 2 and renamed.entry == "src/main.py"
        removed = await project_files.remove(ctx, sid, "src/util.py", version=2)
        assert removed.files_version == 3
        await db.commit()
    async with db_session_factory() as db:
        stored = await sessions.get(_context(db), sid)
        assert stored.files == {"src/main.py": ""}


async def test_deleting_the_entry_requires_an_existing_replacement(
    db_session: AsyncSession,
) -> None:
    ctx = _context(db_session)
    started = await sessions.open_session(ctx, None, None)
    sid = started.id
    await project_files.create(ctx, sid, "package/main.py", "print('bonjour')", version=0)
    with pytest.raises(AppError) as no_entry:
        await project_files.remove(ctx, sid, "main.py", version=1)
    assert no_entry.value.code == "entry_missing"
    with pytest.raises(AppError) as missing:
        await project_files.remove(ctx, sid, "main.py", version=1, replacement_entry="absent.py")
    assert missing.value.code == "entry_missing"
    removed = await project_files.remove(
        ctx, sid, "main.py", version=1, replacement_entry="package/main.py"
    )
    assert removed.entry == "package/main.py" and removed.files_version == 2


@pytest.mark.parametrize("name", ["../f.py", "z//f.py", "/f.py", "C:\\f.py", "a/" * 8 + "f.py"])
async def test_file_paths_follow_the_sandbox_tree(db_session: AsyncSession, name: str) -> None:
    ctx = _context(db_session)
    started = await sessions.open_session(ctx, None, None)
    with pytest.raises(AppError) as invalid:
        await project_files.create(ctx, started.id, name, "contenu fictif", version=0)
    assert invalid.value.status_code == 422 and invalid.value.details is None
    assert started.files == {"main.py": ""} and started.files_version == 0


async def test_file_limits_use_encoded_size_and_a_real_file_tree(db_session: AsyncSession) -> None:
    ctx = _context(db_session)
    started = await sessions.open_session(ctx, None, None)
    state = await sessions.save_files(
        ctx, started.id, {f"p{i}.py": "" for i in range(MAX_FILES)}, "p0.py"
    )
    with pytest.raises(AppError) as too_many:
        await project_files.create(ctx, state.id, "nouveau.py", "", version=1)
    assert too_many.value.code == "files_too_large"
    state = await sessions.save_files(ctx, started.id, {"main.py": ""}, "main.py")
    with pytest.raises(AppError) as too_long:
        await project_files.create(ctx, state.id, "texte.txt", "é" * MAX_TOTAL_BYTES, version=2)
    assert too_long.value.code == "files_too_large"
    with pytest.raises(AppError) as invalid_tree:
        await project_files.create(ctx, state.id, "main.py/enfant.py", "", version=2)
    assert invalid_tree.value.code == "project_path_conflict"


async def test_stale_changes_and_other_accounts_cannot_edit_files(db_session: AsyncSession) -> None:
    ctx = _context(db_session)
    started = await sessions.open_session(ctx, None, None)
    await project_files.create(ctx, started.id, "notes.txt", "Fictif", version=0)
    with pytest.raises(AppError) as stale:
        await project_files.rename(ctx, started.id, "notes.txt", "autre.txt", version=0)
    assert stale.value.status_code == 409
    with pytest.raises(AppError) as private:
        await project_files.remove(
            _context(db_session, "autre"), started.id, "notes.txt", version=1
        )
    assert private.value.status_code == 404
    assert (await sessions.get(ctx, started.id)).files["notes.txt"] == "Fictif"
