"""Catalogue des événements temps réel d'une session (SPEC 9.5, plus `user.message`, D4).

Chaque événement porte l'enveloppe commune (`id`, `session_id`, `seq`, `ts`, `agent`), un `type`
discriminant et une charge typée. L'union `SessionEvent` est publiée dans l'OpenAPI (voir
`openapi.py`) : c'est ainsi que le front reçoit les types du WebSocket (D10).
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

EventType = Literal[
    "agent.started",
    "agent.token",
    "agent.message",
    "tool.called",
    "tool.result",
    "source.found",
    "board.update",
    "memory.written",
    "interrupt.requested",
    "proposal.ready",
    "artifact.ready",
    "cost.updated",
    "run.completed",
    "run.failed",
    "user.message",
]


# --- Charges -------------------------------------------------------------------------------


class AgentStartedPayload(BaseModel):
    step: str
    intent: str  # phrase d'intention affichée : jamais un raisonnement brut (9.5)


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


class BoardUpdatePayload(BaseModel):
    mermaid: str
    step: int


class MemoryWrittenPayload(BaseModel):
    item_id: str
    kind: str
    title: str
    reason: str


class InterruptOption(BaseModel):
    value: str
    label: str


class InterruptRequestedPayload(BaseModel):
    """`kind` et non `type` : `type` est déjà le discriminant de l'enveloppe (DECISIONS)."""

    interrupt_id: str
    kind: str
    question: str
    options: list[InterruptOption] = Field(default_factory=list)


class ProposalReadyPayload(BaseModel):
    proposal_id: str
    title: str


class ArtifactReadyPayload(BaseModel):
    artifact_id: str
    kind: str
    title: str
    url: str | None = None


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


class UserMessagePayload(BaseModel):
    text: str


PAYLOAD_MODELS: dict[EventType, type[BaseModel]] = {
    "agent.started": AgentStartedPayload,
    "agent.token": AgentTokenPayload,
    "agent.message": AgentMessagePayload,
    "tool.called": ToolCalledPayload,
    "tool.result": ToolResultPayload,
    "source.found": SourceFoundPayload,
    "board.update": BoardUpdatePayload,
    "memory.written": MemoryWrittenPayload,
    "interrupt.requested": InterruptRequestedPayload,
    "proposal.ready": ProposalReadyPayload,
    "artifact.ready": ArtifactReadyPayload,
    "cost.updated": CostUpdatedPayload,
    "run.completed": RunCompletedPayload,
    "run.failed": RunFailedPayload,
    "user.message": UserMessagePayload,
}


# --- Enveloppes ----------------------------------------------------------------------------


class EventBase(BaseModel):
    id: str
    session_id: str
    seq: int
    ts: datetime
    agent: str | None = None


class AgentStartedEvent(EventBase):
    type: Literal["agent.started"]
    payload: AgentStartedPayload


class AgentTokenEvent(EventBase):
    type: Literal["agent.token"]
    payload: AgentTokenPayload


class AgentMessageEvent(EventBase):
    type: Literal["agent.message"]
    payload: AgentMessagePayload


class ToolCalledEvent(EventBase):
    type: Literal["tool.called"]
    payload: ToolCalledPayload


class ToolResultEvent(EventBase):
    type: Literal["tool.result"]
    payload: ToolResultPayload


class SourceFoundEvent(EventBase):
    type: Literal["source.found"]
    payload: SourceFoundPayload


class BoardUpdateEvent(EventBase):
    type: Literal["board.update"]
    payload: BoardUpdatePayload


class MemoryWrittenEvent(EventBase):
    type: Literal["memory.written"]
    payload: MemoryWrittenPayload


class InterruptRequestedEvent(EventBase):
    type: Literal["interrupt.requested"]
    payload: InterruptRequestedPayload


class ProposalReadyEvent(EventBase):
    type: Literal["proposal.ready"]
    payload: ProposalReadyPayload


class ArtifactReadyEvent(EventBase):
    type: Literal["artifact.ready"]
    payload: ArtifactReadyPayload


class CostUpdatedEvent(EventBase):
    type: Literal["cost.updated"]
    payload: CostUpdatedPayload


class RunCompletedEvent(EventBase):
    type: Literal["run.completed"]
    payload: RunCompletedPayload


class RunFailedEvent(EventBase):
    type: Literal["run.failed"]
    payload: RunFailedPayload


class UserMessageEvent(EventBase):
    type: Literal["user.message"]
    payload: UserMessagePayload


SessionEvent = Annotated[
    AgentStartedEvent
    | AgentTokenEvent
    | AgentMessageEvent
    | ToolCalledEvent
    | ToolResultEvent
    | SourceFoundEvent
    | BoardUpdateEvent
    | MemoryWrittenEvent
    | InterruptRequestedEvent
    | ProposalReadyEvent
    | ArtifactReadyEvent
    | CostUpdatedEvent
    | RunCompletedEvent
    | RunFailedEvent
    | UserMessageEvent,
    Field(discriminator="type"),
]

SESSION_EVENT_ADAPTER: TypeAdapter[SessionEvent] = TypeAdapter(SessionEvent)


def validate_payload(type: EventType, payload: BaseModel | dict[str, Any]) -> BaseModel:
    """Valide `payload` pour `type` et renvoie le modèle ; `ValueError` si type ou forme invalides.

    Le message d'erreur ne reprend jamais les valeurs reçues (elles peuvent contenir des clés).
    """
    model = PAYLOAD_MODELS.get(type)
    if model is None:
        raise ValueError(f"Type d'événement inconnu : {type!r}")
    if isinstance(payload, model):
        return payload
    if isinstance(payload, BaseModel):
        raise ValueError(f"Charge {payload.__class__.__name__} incompatible avec {type!r}")
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        fields = ", ".join(".".join(str(p) for p in e["loc"]) or "(racine)" for e in exc.errors())
        raise ValueError(f"Charge invalide pour {type!r} : {fields}") from None
