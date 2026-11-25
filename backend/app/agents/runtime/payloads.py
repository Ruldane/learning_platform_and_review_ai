"""Typed payloads of a session's events (SPEC 9.5); the envelope, the catalog and the
validation live in `events.py`, which re-exports them.

Every field added has a default value: events already stored remain valid.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentStartedPayload(BaseModel):
    step: str
    intent: str  # display intent phrase: never a raw reasoning (9.5)


class AgentTokenPayload(BaseModel):
    message_id: str
    text: str


class Citation(BaseModel):
    index: int
    title: str
    url: str | None = None
    memory_item_id: str | None = None


class AgentMessagePayload(BaseModel):
    message_id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)


class ToolCalledPayload(BaseModel):
    call_id: str
    tool: str
    args: dict[str, Any]


class ToolResultPayload(BaseModel):
    call_id: str
    tool: str
    ok: bool
    summary: str


class SourceFoundPayload(BaseModel):
    title: str
    url: str
    author: str | None
    date: str | None
    lang: str | None
    score: int | None
    # Web search additions (D77): default values, so compatible with the
    # events already stored.
    source_id: str | None = None  # absent: page without a `sources` row (excluded domain)
    status: Literal["ok", "unreadable"] = "ok"
    verdict: Literal["kept", "rejected"] | None = None  # absent: source not rated
    reason: str | None = None  # verdict reason, or unreadability
    # Practitioners spotted by the Scout (phase 4, D82): `person`, with their public role.
    kind: Literal["page", "person"] = "page"
    role: str | None = None


BoardKind = Literal["domain_map", "prerequisites", "timeline", "comparison"]


class BoardUpdatePayload(BaseModel):
    """A board state. `board_id`, `kind` and `title` (D82) allow several boards per session
    (domain map, prerequisites, timeline, comparison); they are absent from older events."""

    mermaid: str
    step: int
    board_id: str | None = None
    kind: BoardKind | None = None
    title: str | None = None


class MemoryWrittenPayload(BaseModel):
    item_id: str
    kind: str
    title: str
    reason: str
    status: Literal["active", "pending"] = "active"  # `pending`: "To confirm" decision (D68)


class InterruptOption(BaseModel):
    value: str
    label: str


def _optional_in_schema(schema: dict[str, Any]) -> None:
    """No `default` in the schema: the key is omitted when empty, the client reads it as
    optional."""
    schema.pop("default", None)


class InterruptField(BaseModel):
    """A question of a multi-field scoping step (D82); the resume payload carries
    `{"answers": {id: text}}` (or an option value, `"go"`, D84). A confirmation with
    prefilled fields (`value`) resumes with `{"choice": option, "fields": {id: text}}` (D141)."""

    id: str = Field(pattern=r"^[a-z0-9_]{1,32}$")
    label: str
    required: bool = False
    max_length: int = Field(default=2000, ge=1, le=20000)  # text of a pasted page (F6)
    # Pre-filled value that January corrects (one-sentence record, D141); without it the key is
    # not written: existing questions keep exactly their form.
    value: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        json_schema_extra=_optional_in_schema,
    )


class InterruptRequestedPayload(BaseModel):
    """`kind` rather than `type`: `type` is already the envelope discriminator (DECISIONS)."""

    interrupt_id: str
    kind: str
    question: str
    options: list[InterruptOption] = Field(default_factory=list)
    fields: list[InterruptField] = Field(default_factory=list)


class ProposalReadyPayload(BaseModel):
    proposal_id: str
    title: str


class ArtifactInfo(BaseModel):
    """Information attached to an artifact: an entry close to the one just created
    ("same company within 30 days", SPEC 6.3), with the server's message."""

    application_id: str
    company: str
    title: str
    status: str
    message: str


class ArtifactReadyPayload(BaseModel):
    artifact_id: str
    kind: str
    title: str
    url: str | None = None
    info: list[ArtifactInfo] = Field(default_factory=list)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Without information, the `info` key is not written: other artifacts keep their
        earlier payload (events already stored, and those of graphs that have none)."""
        data = super().model_dump(**kwargs)
        if not data.get("info"):
            data.pop("info", None)
        return data


class CostUpdatedPayload(BaseModel):
    tokens_in: int
    tokens_out: int
    cost_usd: float
    cap_tokens: int


class RunCompletedPayload(BaseModel):
    summary: str = ""


class RunFailedPayload(BaseModel):
    code: str
    message: str


# Permanent debate commands (SPEC 3.2) carried by `user.message` (D82).
UserCommand = Literal["another_round", "to_proposals", "more_concrete", "shorter"]


class UserMessagePayload(BaseModel):
    """A user message (D4); `command` is the debate command, and text is then optional."""

    text: str = ""
    command: UserCommand | None = None
