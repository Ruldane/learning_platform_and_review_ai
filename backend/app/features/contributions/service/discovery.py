"""Suggestions drawn from the program's repositories and the current module's skills."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models.program import Module
from app.features.contributions.service.matching import Suggestion, rank_issues
from app.features.lessons.service.resources import repository_resources
from app.features.program.service.programs import Loaded, load
from app.providers.github.base import GithubContributions, RepoRef

_MAX_REPOS = 3
_MAX_SUGGESTIONS = 12


@dataclass(frozen=True)
class ChapterContext:
    module_id: str
    title: str
    skills: tuple[str, ...]
    repositories: tuple[RepoRef, ...]


def _chapter(loaded: Loaded) -> Module | None:
    modules = [mod for mod in loaded.modules if not mod.skipped and mod.kind != "validation"]
    return next(
        (
            module
            for module in modules
            if any(task.status != "done" for task in loaded.tasks_of_module(module.id))
        ),
        modules[-1] if modules else None,
    )


async def chapter_context(db: AsyncSession, user_id: str, program_id: str) -> ChapterContext | None:
    loaded = await load(db, user_id, program_id)
    module = _chapter(loaded)
    if module is None:
        return None
    metadata = await repository_resources(db, user_id, program_id)
    sources = sorted(metadata, key=lambda row: row[0] != module.id)
    refs = tuple(dict.fromkeys(ref for _, url in sources if (ref := RepoRef.from_url(url))))
    skills = tuple(name for name in module.skills if isinstance(name, str) and name.strip())
    return ChapterContext(module.id, module.title, skills, refs[:_MAX_REPOS])


async def suggestions(
    factory: async_sessionmaker[AsyncSession],
    github: GithubContributions,
    user_id: str,
    program_id: str,
) -> tuple[ChapterContext | None, list[Suggestion]]:
    async with factory() as db:
        context = await chapter_context(db, user_id, program_id)
    if context is None or not context.skills:
        return context, []
    results: list[Suggestion] = []
    read = 0
    for repo in context.repositories:
        try:
            issues = await github.open_issues(repo)
        except AppError:
            continue
        results.extend(rank_issues(repo, issues, context.skills))
        read += 1
    if context.repositories and not read:
        raise AppError("github_unavailable", "GitHub could not be read. Try again later.", 502)
    results.sort(key=lambda item: (-len(item.skills), item.repo.name, item.issue.number))
    return context, results[:_MAX_SUGGESTIONS]
