"""Schemas and constants of the Scout (SPEC 9.1, 10.3). The score bounds are those of the
scale: the schema enforces them, an out-of-scale score makes the model replay then fail
readably (`structured_output_invalid`), never pass."""

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose
from app.agents.state.web_research import WebResearchState

AGENT = "scout"
MAX_PAGES_PER_RUN = 10  # also bounded by the session's page cap
MAX_EXTRA_URLS = 5  # addresses given as input, read in addition to the results
# Pages scored at most by a `judge` node: results read plus the input's addresses.
MAX_PAGES_JUDGED = MAX_PAGES_PER_RUN + MAX_EXTRA_URLS
PAGE_CHARS_FOR_SCORING = 6000
MAX_QUERIES_TOTAL = 6
QUERIES_PER_LANGUAGE = 3


class Node(Protocol):
    """Shape of a node (parameter named `state`, as `StateGraph.add_node` expects)."""

    async def __call__(self, state: WebResearchState) -> WebResearchState: ...


class PlannedQuery(BaseModel):
    text: str = Field(min_length=2, max_length=200)
    lang: str = Field(pattern=r"^[a-z]{2}$")


class SearchPlan(BaseModel):
    queries: list[PlannedQuery] = Field(min_length=1, max_length=MAX_QUERIES_TOTAL)


class SourceScore(BaseModel):
    """Scale of 10.3: authority 30 + freshness 20 + depth 20 + real author 15 + teaching
    quality 15. The model does not give the total: the code adds it up."""

    authority: int = Field(ge=0, le=30)
    freshness: int = Field(ge=0, le=20)
    depth: int = Field(ge=0, le=20)
    author: int = Field(ge=0, le=15)
    pedagogy: int = Field(ge=0, le=15)
    reason: Prose = Field(min_length=1, max_length=300)
    summary: Prose = Field(min_length=1, max_length=600)

    @property
    def total(self) -> int:
        return self.authority + self.freshness + self.depth + self.author + self.pedagogy

    @property
    def criteria(self) -> dict[str, int]:
        return {
            "authority": self.authority,
            "freshness": self.freshness,
            "depth": self.depth,
            "author": self.author,
            "pedagogy": self.pedagogy,
        }


def one_line(text: str) -> str:
    return " ".join(text.split())


def page_title(page: dict[str, Any]) -> str:
    """Page title on one line, otherwise its address."""
    return one_line(page.get("title") or "") or str(page["url"])
