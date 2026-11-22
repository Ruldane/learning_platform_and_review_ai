from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.providers.github.base import GithubContributions


@dataclass(frozen=True)
class ContributionRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    github: GithubContributions
