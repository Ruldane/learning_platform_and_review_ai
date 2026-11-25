"""Port of the master profile (SPEC 5.1, D124). `app.agents` imports no feature (contract 6): it
describes here what the Archivist needs in `profile` mode (January's document text, the last
validated version, the draft write); the `cv` feature implements it
(`AgentProfileStore`, 6.8).

The text of a CV, of a LinkedIn profile and January's note are personal data and untrusted
content (17.2, 17.4): never logged, neither here nor by the implementation.

`save_draft` is idempotent per session: a node replayed after a stop (SPEC 9.4) returns the number
of the draft already written, without writing a second one."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.tools.cv_schema import MasterProfileData
from app.core.errors import AppError

SourceKind = Literal["cv", "linkedin", "note"]
MAX_SOURCE_CHARS = 40_000  # text of a source shown to the Archivist (cut beyond)
MAX_NOTE_CHARS = 4_000
MAX_HIDDEN_LINES = 20  # lines of invisible text kept to show them to January


@dataclass(frozen=True)
class ProfileSource:
    """A profile source: the visible text of a PDF (in stream order) or the note."""

    kind: SourceKind
    text: str  # `MAX_SOURCE_CHARS` at most


@dataclass(frozen=True)
class ProfileSources:
    """The sources in CV, LinkedIn, note order; `previous`: last validated version.
    `hidden`: text of the invisible lines of PDFs (white text, tiny, off page), never
    shown to the Archivist and reported to January in `dropped` (preflight G6)."""

    sources: list[ProfileSource]
    previous: MasterProfileData | None
    hidden: list[str] = field(default_factory=list)


class ProfileStore(Protocol):
    async def sources(
        self, user_id: str, document_ids: Sequence[str], note: str | None
    ) -> ProfileSources:
        """The PDFs stored in memory, reread by their file and layout (visible blocks
        only), cut at `MAX_SOURCE_CHARS`; the note last. Missing document or another's:
        404 `document_not_found`; unreadable PDF: `PdfUnreadable`."""
        ...

    async def save_draft(
        self, user_id: str, session_id: str, draft: MasterProfileData, dropped: Sequence[str]
    ) -> int:
        """Idempotent per session (draft already written -> its number). Merge with the last
        validated version (a fact with the same normalized text keeps its id), new ids never reused
        from a past version (`assign_fact_ids` last); returns the version number."""
        ...


def profile_unavailable() -> AppError:
    return AppError(
        "profile_unavailable", "The master profile is unavailable in this runtime.", 503
    )


class _NoProfile:
    """Engine default value (tests, starts without the feature)."""

    async def sources(
        self, user_id: str, document_ids: Sequence[str], note: str | None
    ) -> ProfileSources:
        raise profile_unavailable()

    async def save_draft(
        self, user_id: str, session_id: str, draft: MasterProfileData, dropped: Sequence[str]
    ) -> int:
        raise profile_unavailable()


NO_PROFILE: ProfileStore = _NoProfile()
