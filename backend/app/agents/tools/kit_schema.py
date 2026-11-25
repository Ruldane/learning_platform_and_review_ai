"""Schemas for the seven application kit pieces and the company dossier (SPEC 6.4, F16, D142).

Drafts expose `parts()` for claim checks and word counts, `limits` for each bounded
part, and `render()` for storage. Drafts outside the limits after one retry need review.

Saved follow-ups put the 7-day email before a line of three dashes and the 14-day email
after it (SPEC 7.3). LinkedIn drafts use the same separator between invitation and message.
Company dossiers cite pages by number. The dossier checks drop claims without read sources.
"""

import datetime as dt
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.agents.runtime.prose import Prose
from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.salary import is_salary_question
from app.db.models.applications import KitKind, KitStatus

__all__ = [
    "KIT_KINDS",
    "KIT_TITLES",
    "CompanyDossier",
    "CvVersionRef",
    "Draft",
    "FormAnswer",
    "FormAnswers",
    "Followups",
    "KitContext",
    "KitKind",
    "KitStatus",
    "Letter",
    "LinkedInMessages",
    "NewsItem",
    "Pitch",
    "SourceRef",
    "is_separator",
    "join_parts",
    "split_followups",
    "split_parts",
]

KIT_KINDS: tuple[KitKind, ...] = (
    "cv",
    "letter",
    "linkedin",
    "followups",
    "form_answers",
    "company_brief",
    "pitch",
)
KIT_TITLES: dict[KitKind, str] = {
    "cv": "Tailored résumé",
    "letter": "Cover letter",
    "linkedin": "LinkedIn message",
    "followups": "Follow-ups",
    "form_answers": "Form answers",
    "company_brief": "Company brief",
    "pitch": "Elevator pitch",
}
SEPARATOR = "---"
SALARY_BLANK = "For you to fill in"
TO_COMPLETE = "To complete"
NO_QUESTION = "No screening questions were found in the posting."


def is_separator(line: str) -> bool:
    """A line of at least three dashes, optionally surrounded by whitespace."""
    stripped = line.strip()
    return len(stripped) >= len(SEPARATOR) and set(stripped) == {"-"}


def split_parts(content: str) -> list[str]:
    """Split a stored piece for the graph, route, and follow-up drafts."""
    parts: list[list[str]] = [[]]
    for line in content.splitlines():
        if is_separator(line):
            parts.append([])
        else:
            parts[-1].append(line)
    return ["\n".join(lines).strip() for lines in parts]


def split_followups(content: str) -> tuple[str, str]:
    """Use the first and last sections as the 7-day and 14-day emails."""
    parts = split_parts(content)
    return parts[0], parts[-1] if len(parts) > 1 else ""


def join_parts(first: str, second: str) -> str:
    """Remove separators within each part and join the two parts with one separator."""
    clean = [
        "\n".join(line for line in text.splitlines() if not is_separator(line)).strip()
        for text in (first, second)
    ]
    return f"{clean[0]}\n\n{SEPARATOR}\n\n{clean[1]}"


class Draft(BaseModel):
    """A text draft with parts to check, word limits, and a storage representation."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {}

    def parts(self) -> dict[str, str]:
        raise NotImplementedError

    def render(self) -> str:
        raise NotImplementedError


class Letter(Draft):
    """A 250- to 350-word cover letter."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"text": (250, 350)}
    text: Prose = Field(min_length=1, max_length=4000)

    def parts(self) -> dict[str, str]:
        return {"text": self.text}

    def render(self) -> str:
        return self.text.strip()


class LinkedInMessages(Draft):
    """A connection request of up to 300 characters and a message of up to 150 words."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"message": (1, 150)}
    invitation: str = Field(min_length=1, max_length=300)
    message: Prose = Field(min_length=1, max_length=2000)

    def parts(self) -> dict[str, str]:
        return {"invitation": self.invitation, "message": self.message}

    def render(self) -> str:
        return join_parts(self.invitation, self.message)


class Followups(Draft):
    """Follow-up emails for days 7 and 14, up to 120 words each."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"day_7": (1, 120), "day_14": (1, 120)}
    day_7: Prose = Field(min_length=1, max_length=2000)
    day_14: Prose = Field(min_length=1, max_length=2000)

    def parts(self) -> dict[str, str]:
        return {"day_7": self.day_7, "day_14": self.day_14}

    def render(self) -> str:
        return join_parts(self.day_7, self.day_14)


class Pitch(Draft):
    """A 130- to 170-word answer to “Tell me about yourself,” about a minute aloud."""

    limits: ClassVar[dict[str, tuple[int, int]]] = {"text": (130, 170)}
    text: Prose = Field(min_length=1, max_length=2000)

    def parts(self) -> dict[str, str]:
        return {"text": self.text}

    def render(self) -> str:
        return self.text.strip()


class FormAnswer(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(max_length=800)
    fact_ids: list[str] = Field(default_factory=list, max_length=10)  # Supporting facts.

    @property
    def state(self) -> Literal["ok", "salary", "to_complete"]:
        """Distinguish a supported answer, a salary question, and an unsupported answer."""
        if self.answer.strip():
            return "ok"
        return "salary" if is_salary_question(self.question) else "to_complete"


class FormAnswers(Draft):
    """Answers to the posting's screening questions based only on the profile."""

    items: list[FormAnswer] = Field(default_factory=list, max_length=10)

    def parts(self) -> dict[str, str]:
        return {f"answer_{rank}": item.answer for rank, item in enumerate(self.items, 1)}

    def render(self) -> str:
        if not self.items:
            return NO_QUESTION
        blanks = {"salary": SALARY_BLANK, "to_complete": TO_COMPLETE}
        lines = []
        for item in self.items:
            body = item.answer if item.state == "ok" else blanks[item.state]
            lines.append(f"### {item.question}\n{body}")
        return "\n\n".join(lines)


Cited = Annotated[str, Field(min_length=1, max_length=300)]


class NewsItem(BaseModel):
    """A news item from the past six months with a numbered citation in its text."""

    text: Prose = Field(min_length=1, max_length=300)
    date: dt.date | None = None


_LEGACY_COMPANY_SIZES = {"pme": "sme", "grand_groupe": "large_company", "inconnu": "unknown"}


def _company_size(value: object) -> object:
    return _LEGACY_COMPANY_SIZES.get(value, value) if isinstance(value, str) else value


CompanySize = Annotated[
    Literal["startup", "sme", "large_company", "unknown"], BeforeValidator(_company_size)
]


class CompanyDossier(BaseModel):
    """A one-page company dossier with numbered citations for each claim (F16)."""

    activity: Prose = Field(max_length=700)
    product: Prose = Field(max_length=700)
    stack: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=15
    )
    news: list[NewsItem] = Field(default_factory=list, max_length=8)
    culture: Prose = Field(max_length=700)
    interview_process: Prose = Field(max_length=700)
    questions: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        min_length=5, max_length=5
    )
    watch_points: list[Cited] = Field(default_factory=list, max_length=6)
    size: CompanySize = "unknown"


class SourceRef(BaseModel):
    """A page cited in the dossier using its one-based position."""

    url: str = Field(max_length=2048)
    title: str = Field(default="", max_length=300)
    source_id: str | None = None


class CvVersionRef(BaseModel):
    """The posting's latest ready résumé version."""

    version_id: str
    number: int = Field(ge=1)


class KitContext(BaseModel):
    """Read-only inputs for the kit, including a validated profile and analyzed posting.

    Reuse a dossier younger than 30 days with its source pages. Keep user-edited pieces
    on regeneration. `today` uses the user's time zone.
    """

    application_id: str
    language: Literal["fr", "en"]
    today: dt.date
    posting_text: str
    analysis: PostingAnalysis
    company: str
    title: str
    contact: str | None = None
    profile: MasterProfileData
    company_dossier: CompanyDossier | None = None
    company_dossier_sources: list[SourceRef] = Field(default_factory=list)
    cv_version: CvVersionRef | None = None
    keep: list[KitKind] = Field(default_factory=list)
