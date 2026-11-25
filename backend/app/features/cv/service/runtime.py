"""The CV in the life of the application (D124, D126): what the master profile and template
routes share with the ports of the Archivist (`AgentProfileStore`) and of the Layout designer
(`AgentCvTemplateStore`): database, memory (stored documents, re-read files, storage of images
and fonts), session launcher (linked to the engine later), PDF layout, rendering of our HTML
templates, free fonts and locks. Created by the lifespan before the agent engine
(`app.state.career.cv`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.core.portfolio_urls import no_origin
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.service.runtime import KeyLocks
from app.providers.fonts.base import FontSource
from app.providers.pdf.base import HtmlPdfRenderer, PdfLayoutExtractor
from app.providers.storage.base import FileStorage

CAPTURE_GRAPH = "cv_capture"
PROFILE_SUBJECT = "master_profile"
TEMPLATE_SUBJECT = "cv_template"
REVIEW_GRAPH = "cv_review"
REVIEW_SUBJECT = "cv_review"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Resumer(Protocol):
    """Resumes a pending question (`SessionLauncher.resume`, D130): "Generate the PDF" answers the
    review's exit question."""

    async def resume(
        self, user_id: str, session_id: str, interrupt_id: str, value: Any
    ) -> None: ...


class _NoResumer:
    """Default value (port tests, startups without an engine): engine unavailable."""

    async def resume(self, user_id: str, session_id: str, interrupt_id: str, value: Any) -> None:
        raise AppError("engine_unavailable", "The agent service isn't ready yet.", 503)


@dataclass
class CvRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    memory: MemoryRuntime
    launcher: Launcher
    layout: PdfLayoutExtractor
    html_pdf: HtmlPdfRenderer
    fonts: FontSource
    now: Callable[[], datetime] = utc_now
    resumer: Resumer = field(default_factory=_NoResumer)
    _versions: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _imports: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _templates: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    _reviews: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)
    # Company record creation: the same `KeyLocks` as the applications (M7).
    company_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
    portfolio_origin: Callable[[], str | None] = no_origin

    @property
    def storage(self) -> FileStorage:
        """Memory storage: page images and template fonts (D119)."""
        return self.memory.providers.storage

    def version_lock(self, user_id: str) -> asyncio.Lock:
        """One new profile version at a time per user (Archivist draft, January's version): numbers
        without a race. Specific to this process (a single worker); the unique index
        `(user_id, version)` remains the last line of defense."""
        return self._versions.setdefault(user_id, asyncio.Lock())

    def import_lock(self, user_id: str) -> asyncio.Lock:
        """Starts a capture unless one is already open: a double send starts only one capture."""
        return self._imports.setdefault(user_id, asyncio.Lock())

    def template_lock(self, user_id: str) -> asyncio.Lock:
        """Templates of the user: creation and launch of the capture, status reconciled with the
        session, active template (only one, partial unique index); never during a render."""
        return self._templates.setdefault(user_id, asyncio.Lock())

    def review_lock(self, user_id: str) -> asyncio.Lock:
        """Reviews of the user (D130): launch, status reconciled with the session, decisions,
        click on "Generate" (decisions frozen, one version rendering at a time); never during the
        render itself, which the flow does outside this lock."""
        return self._reviews.setdefault(user_id, asyncio.Lock())
