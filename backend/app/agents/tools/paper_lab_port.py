"""Données du parcours qui transforme un article lu en exercice Python."""

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

PAPER_GRAPH = "paper_lab"


class ExperimentDraft(BaseModel):
    method: str = Field(min_length=20, max_length=1800)
    code: str = Field(min_length=10, max_length=18_000)
    expected: str = Field(min_length=12, max_length=1200)


class PaperDraft(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    course: str = Field(min_length=150, max_length=20_000)
    experiment: ExperimentDraft


@dataclass(frozen=True)
class ArticleSource:
    url: str
    title: str
    material: str


@dataclass(frozen=True)
class PaperLabContext:
    url: str
    published: bool


class PaperLabStore(Protocol):
    async def context(self, user_id: str, lab_id: str, session_id: str) -> PaperLabContext: ...

    async def publish(
        self, user_id: str, lab_id: str, session_id: str, source: ArticleSource, draft: PaperDraft
    ) -> None: ...


class _MissingPaperLab:
    async def context(self, user_id: str, lab_id: str, session_id: str) -> PaperLabContext:
        raise RuntimeError("Le parcours Du papier au code n’est pas branché.")

    async def publish(
        self, user_id: str, lab_id: str, session_id: str, source: ArticleSource, draft: PaperDraft
    ) -> None:
        raise RuntimeError("Le parcours Du papier au code n’est pas branché.")


NO_PAPER_LAB: PaperLabStore = _MissingPaperLab()
