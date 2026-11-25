from datetime import date, datetime

from pydantic import BaseModel


class CostTotals(BaseModel):
    """Calls, tokens and cost of a group of calls; `estimated_calls`: how many of these calls
    have an estimated cost (the provider did not return its tokens)."""

    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    estimated_calls: int


class CostRow(CostTotals):
    """A report row. `key`: the day (`2026-11-16`), the graph (`""` outside a session), the
    agent (`""` none) or `provider:model` (`glm:glm-5.3-flash`)."""

    key: str


class CostsReport(BaseModel):
    """Costs over the last `days` local days, from `since` to `until` inclusive; days without
    calls are present, at zero."""

    days: int
    since: date
    until: date
    total: CostTotals
    by_day: list[CostRow]
    by_feature: list[CostRow]
    by_agent: list[CostRow]
    by_model: list[CostRow]


class AgentCallOut(BaseModel):
    """A call to a model, as logged: never the prompt content."""

    id: str
    at: datetime
    session_id: str | None
    graph: str | None
    agent: str | None
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float
    estimated: bool


class AgentCallPage(BaseModel):
    """A page of the log; `next_before` (opaque cursor) gives the next page, `None` at the
    end."""

    items: list[AgentCallOut]
    next_before: str | None
