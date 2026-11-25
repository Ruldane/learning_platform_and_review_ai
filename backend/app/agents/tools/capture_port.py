"""Port of the quick capture (SPEC F18, D108). `app.agents` imports no feature (contract 6):
it describes here what the `capture` graph needs (an imported document, links to the
program, the filing of the capture, the ticked task, the cards); the `capture` feature
implements it (`AgentCaptureStore`).

The Archivist links the capture to the program by references (`m3`, `t12`): the real ids
(`ModuleRef.module_id`, `TaskRef.task_id`) are never shown to the model (F7). The graph
keeps the snapshot of the links in its state; `store` receives this snapshot and `tick_task` the id
resolved from it.

Each write is idempotent: `store` per session (journal line "capture:{session}"),
`tick_task` (a done task stays done), `add_cards` (deduplicated by front). A replayed node
after a stop (SPEC 9.4) never writes anything more.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.prose import ShortenToMax
from app.agents.tools.replan_port import MODULE_REF, TASK_REF, ModuleRef, TaskRef
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError

CaptureSource = Literal["url", "text", "document"]
SUMMARY_LINES = 5
CAPTURE_REASON = "January's quick capture."
# Beyond that, typed text is read as pasted text (copied article), never as a note from
# January: it declares no skill (D108 no. 4, final review of phase 5).
NOTE_MAX_CHARS = 1_000

SummaryLine = Annotated[str, Field(max_length=200), ShortenToMax()]
ConceptName = Annotated[str, Field(min_length=2, max_length=120)]
ModuleRefText = Annotated[str, Field(pattern=MODULE_REF)]


@dataclass(frozen=True)
class CaptureMaterial:
    """What the Archivist reads: the page, the document or January's text. `url`: the address
    read (normalized), that of a document imported by link, otherwise `None`."""

    title: str
    text: str
    url: str | None


def is_note(source: CaptureSource, text: str) -> bool:
    """A note from January: a typed text (source `text`) and short. Only a note can
    declare "I learned X"; a page, a document or a long pasted text, never."""
    return source == "text" and len(text) <= NOTE_MAX_CHARS


class CaptureDigest(BaseModel):
    """The capture summarized by the Archivist (structured output)."""

    title: str = Field(min_length=3, max_length=120)
    summary: list[SummaryLine] = Field(min_length=1, max_length=SUMMARY_LINES)
    concepts: list[ConceptName] = Field(default_factory=list, max_length=10)
    modules: list[ModuleRefText] = Field(default_factory=list, max_length=5)
    covered_task: str | None = Field(default=None, pattern=TASK_REF)
    learned: bool = False  # "I learned X": concepts -> skills `declare` (January's note)
    flashcards: list[CardDraft] = Field(default_factory=list, max_length=5)


@dataclass(frozen=True)
class ProgramLinks:
    """Modules of validated programs and tasks due within ± 7 days (January's day)."""

    modules: list[ModuleRef]
    tasks: list[TaskRef]

    def module(self, ref: str) -> ModuleRef | None:
        return next((m for m in self.modules if m.ref == ref), None)

    def task(self, ref: str) -> TaskRef | None:
        return next((t for t in self.tasks if t.ref == ref), None)


NO_LINKS = ProgramLinks([], [])


@dataclass(frozen=True)
class CaptureStored:
    memory_item_id: str
    journal_entry_id: str
    covered_task: TaskRef | None  # the task the capture covers, resolved from `links`


class CaptureStore(Protocol):
    async def document(self, user_id: str, document_id: str) -> CaptureMaterial | None:
        """January's imported document; `None`: not indexed yet. 404
        `document_not_found` if it is not hers, 409 `document_failed` if its import
        failed (it will never be indexed)."""
        ...

    async def links(self, user_id: str) -> ProgramLinks: ...

    async def store(
        self,
        user_id: str,
        session_id: str,
        digest: CaptureDigest,
        material: CaptureMaterial,
        links: ProgramLinks,
        *,
        source: CaptureSource,
    ) -> CaptureStored:
        """Summarized `document` memory item, `declare` skill if `learned`, `capture` journal line;
        idempotent per session (a replay rereads what is stored)."""
        ...

    async def tick_task(self, user_id: str, session_id: str, task_id: str) -> bool:
        """Ticks the task (idempotent); true if ticked, false if it no longer exists
        (removed in the meantime, by an accepted replanning) or is not January's."""
        ...

    async def add_cards(self, user_id: str, session_id: str, cards: Sequence[CardDraft]) -> int:
        """The capture's cards, deduplicated by front; returns the number created."""
        ...


def capture_unavailable() -> AppError:
    return AppError("capture_unavailable", "Capture is unavailable in this runtime.", 503)


class _NoCapture:
    """Engine default value (tests, starts without the feature)."""

    async def document(self, user_id: str, document_id: str) -> CaptureMaterial | None:
        raise capture_unavailable()

    async def links(self, user_id: str) -> ProgramLinks:
        raise capture_unavailable()

    async def store(
        self,
        user_id: str,
        session_id: str,
        digest: CaptureDigest,
        material: CaptureMaterial,
        links: ProgramLinks,
        *,
        source: CaptureSource,
    ) -> CaptureStored:
        raise capture_unavailable()

    async def tick_task(self, user_id: str, session_id: str, task_id: str) -> bool:
        raise capture_unavailable()

    async def add_cards(self, user_id: str, session_id: str, cards: Sequence[CardDraft]) -> int:
        raise capture_unavailable()


NO_CAPTURE: CaptureStore = _NoCapture()
