"""Cost tracking: each LLM call is logged (`llm_calls`), added up in the session, published
live (`cost.updated`); a per-session token cap cuts the following calls (9.6).

A cut call (deadline, `node_timeout`, cancellation, provider error) has no usage returned by
the model: it is counted with **estimated** tokens (`estimated`, D117); input: characters of the
text / 4 (tool definitions and schemas not counted), output: chunks received. A provider error
returned before any chunk (429, 401, 5xx, connection refused) consumed nothing: it counts for
nothing, and neither do its retries. LangChain calls `on_llm_error` only for an error raised
by the model; a cancelled call (`CancelledError`, which is what `asyncio.timeout` and
`node_timeout` do) calls neither `on_llm_end` nor `on_llm_error`: `flush_cut()`, called at the
end of the execution (`runtime/execution.py`), writes those starts left without an end.

`CostTracker` is an asynchronous LangChain callback run on the caller's loop: the bus cannot
publish from another thread (D42), a synchronous callback (run in a thread) is ruled out.
"""

import json
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.repositories import LlmCallRepository, SessionRepository
from app.core.errors import AppError
from app.providers.llm.errors import is_timeout

logger = logging.getLogger(__name__)

_UNKNOWN = "unknown"
APPROX_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class ModelPrice:
    input_per_mtok: float
    output_per_mtok: float


def load_prices(path: Path) -> dict[str, ModelPrice]:
    """Price table (USD per million tokens); `ValueError` if an entry is malformed."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    prices: dict[str, ModelPrice] = {}
    for model, entry in raw.items():
        try:
            prices[model] = ModelPrice(
                float(entry["input_per_mtok"]), float(entry["output_per_mtok"])
            )
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Malformed price for model {model!r}") from None
    return prices


def estimate_cost(
    model: str, tokens_in: int, tokens_out: int, prices: Mapping[str, ModelPrice]
) -> float:
    """Estimated cost in USD; 0.0 for a model absent from the table."""
    price = prices.get(model)
    if price is None:
        return 0.0
    return (tokens_in * price.input_per_mtok + tokens_out * price.output_per_mtok) / 1_000_000


class TokenBudgetExceeded(AppError):
    def __init__(self, cap_tokens: int) -> None:
        super().__init__(
            "token_cap_reached",
            f"Token cap of {cap_tokens} reached for this session.",
            400,
            {"cap_tokens": cap_tokens},
        )


def _chars(message: BaseMessage) -> int:
    """Characters of a message's text; an image (or any other block) counts 0."""
    content = message.content
    if isinstance(content, str):
        return len(content)
    total = 0
    for block in content:
        if isinstance(block, str):
            total += len(block)
        elif block.get("type") == "text":
            total += len(str(block.get("text", "")))
    return total


def approx_tokens(messages: Sequence[Sequence[BaseMessage]]) -> int:
    """Estimate of the input tokens: characters of the text // 4, at least 1."""
    chars = sum(_chars(message) for batch in messages for message in batch)
    return max(1, chars // APPROX_CHARS_PER_TOKEN)


@dataclass(frozen=True)
class _CallStart:
    started: float
    agent: str | None
    provider: str
    model: str
    approx_in: int


def _usage(response: LLMResult) -> tuple[int, int]:
    """Tokens `(input, output)` of the last generated message, `(0, 0)` if the model gives none."""
    for generations in reversed(response.generations):
        for generation in reversed(generations):
            usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
            if usage:
                return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    return 0, 0


class CostTracker(AsyncCallbackHandler):
    raise_error = True  # without it, TokenBudgetExceeded would be swallowed by LangChain
    # Not `run_inline`: an "inline" handler that raises leaves the other handlers' coroutines
    # never awaited (langchain_core, `on_chat_model_start`); grouped with them by
    # `asyncio.gather`, it always runs on the caller's loop (D42, D46).
    run_inline = False

    def __init__(
        self,
        *,
        user_id: str,
        session_id: str,
        graph: str,
        bus: EventBus,
        session_factory: async_sessionmaker[AsyncSession],
        prices: Mapping[str, ModelPrice],
        cap_tokens: int,
    ) -> None:
        self._user_id = user_id
        self._session_id = session_id
        self._graph = graph
        self._bus = bus
        self._factory = session_factory
        self._prices = prices
        self._cap = cap_tokens
        self._calls: dict[UUID, _CallStart] = {}
        self._chunks: dict[UUID, int] = {}  # chunks received per call in progress

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Refuses the call if the session cap is reached, otherwise remembers its start.

        Provider and model: `tremplin_*` metadata set by the providers, failing that the
        `ls_provider` / `ls_model_name` that LangChain infers from the model.
        """
        async with self._factory() as db:
            session = await SessionRepository(db, self._user_id).get(self._session_id)
        if session is not None and session.tokens_in + session.tokens_out >= self._cap:
            raise TokenBudgetExceeded(self._cap)
        meta = metadata or {}
        if meta.get("tremplin_provider") == "mcp":
            return  # The step reservation logs the render only once.
        self._calls[run_id] = _CallStart(
            started=time.monotonic(),
            agent=meta.get("agent"),
            provider=str(meta.get("tremplin_provider") or meta.get("ls_provider") or _UNKNOWN),
            model=str(meta.get("tremplin_model") or meta.get("ls_model_name") or _UNKNOWN),
            approx_in=approx_tokens(messages),
        )

    async def on_llm_new_token(
        self, token: str | list[str | dict[str, Any]], *, run_id: UUID, **kwargs: Any
    ) -> None:
        """A chunk of the reply received (one chunk ~ one token): the output of a cut call."""
        if run_id in self._calls:
            self._chunks[run_id] = self._chunks.get(run_id, 0) + 1

    async def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        """Failed call: counted in estimated tokens if it started answering (chunks received)
        or if it exceeded a deadline; an error returned before any answer (429, 401, 5xx,
        connection refused) counts for nothing. The start is removed at the first end event:
        never two rows for the same `run_id`."""
        await self._record_cut(run_id, only_if_answered=not is_timeout(error))

    async def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._calls.pop(run_id, None)
        self._chunks.pop(run_id, None)
        if start is None:
            return
        await self._record_safely(start, *_usage(response))

    async def flush_cut(self) -> int:
        """Writes, in estimated tokens, the calls that left without `on_llm_end` or `on_llm_error`
        (cancelled); returns their number. Called at the end of the execution, when no call runs."""
        cut = list(self._calls)
        for run_id in cut:
            await self._record_cut(run_id)
        return len(cut)

    async def _record_cut(self, run_id: UUID, *, only_if_answered: bool = False) -> None:
        """`only_if_answered`: nothing is written if no chunk arrived (error returned before
        any answer). Otherwise (cancellation, deadline): the request may have been processed."""
        start = self._calls.pop(run_id, None)
        chunks = self._chunks.pop(run_id, 0)
        if start is None or (only_if_answered and chunks == 0):
            return
        await self._record_safely(start, start.approx_in, chunks, estimated=True)

    async def _record_safely(
        self, start: _CallStart, tokens_in: int, tokens_out: int, *, estimated: bool = False
    ) -> None:
        try:
            await self._record(start, tokens_in, tokens_out, estimated=estimated)
        except Exception:  # accounting must never make the call or its outcome fail
            logger.exception("Cost tracking failed for session %s", self._session_id)

    async def _record(
        self, start: _CallStart, tokens_in: int, tokens_out: int, *, estimated: bool
    ) -> None:
        cost = estimate_cost(start.model, tokens_in, tokens_out, self._prices)
        async with self._factory() as db:
            await LlmCallRepository(db, self._user_id).add(
                session_id=self._session_id,
                graph=self._graph,
                agent=start.agent,
                provider=start.provider,
                model=start.model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=round((time.monotonic() - start.started) * 1000),
                cost_usd=cost,
                estimated=estimated,
            )
            totals = await SessionRepository(db, self._user_id).add_usage(
                self._session_id, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost
            )
            await db.commit()
        if totals is not None:
            await self._bus.publish(
                user_id=self._user_id,
                session_id=self._session_id,
                type="cost.updated",
                payload={
                    "tokens_in": totals[0],
                    "tokens_out": totals[1],
                    "cost_usd": totals[2],
                    "cap_tokens": self._cap,
                },
                agent=start.agent,
            )
