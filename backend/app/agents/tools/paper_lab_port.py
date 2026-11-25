"""Data of the graph that turns a paper that was read into a Python exercise."""

import re
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.errors import AppError

PAPER_GRAPH = "paper_lab"


class ExperimentDraft(BaseModel):
    method: str = Field(min_length=20, max_length=1800)
    code: str = Field(min_length=10, max_length=18_000)
    expected: str = Field(min_length=12, max_length=1200)


class PaperDraft(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    course: str = Field(min_length=150, max_length=20_000)
    source_quote: str = Field(min_length=20, max_length=450)
    experiment: ExperimentDraft


@dataclass(frozen=True)
class ArticleSource:
    url: str
    title: str
    material: str


def cited_course(source: ArticleSource, draft: PaperDraft) -> str:
    """The course quotes a verified excerpt of the text given to the Writer."""
    quote = " ".join(draft.source_quote.split())
    if len(quote) < 20 or quote not in " ".join(source.material.split()):
        raise AppError("paper_lab_citation", "The quoted text does not appear in the paper.", 422)
    literal = re.sub(r"([\\\x60*_{}\[\]()<>#!|])", r"\\\1", quote)
    return f"{draft.course}\n\n## Excerpt from the paper\n\n> {literal}"


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
        raise RuntimeError("The From Paper to Code graph is not wired.")

    async def publish(
        self, user_id: str, lab_id: str, session_id: str, source: ArticleSource, draft: PaperDraft
    ) -> None:
        raise RuntimeError("The From Paper to Code graph is not wired.")


NO_PAPER_LAB: PaperLabStore = _MissingPaperLab()
