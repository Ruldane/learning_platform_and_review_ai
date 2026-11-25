"""Calling a model from a node: intent events, retries with increasing wait on provider
errors, 120 s cap per node (SPEC 9.6, D44).

The factory's models are built without SDK retries (`max_retries=0`): it is here, and only
here, that a call is retried.
"""

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.constants import TAG_NOSTREAM

from app.agents.runtime.emit import emit
from app.core.errors import AppError
from app.providers.llm.base import CALL_DEADLINE_KEY
from app.providers.llm.errors import describe_provider_error, is_transient

logger = logging.getLogger(__name__)

NODE_TIMEOUT_S = 120
RETRY_DELAYS_S = (1.0, 2.0, 4.0)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)  # hook for the tests


def message_text(message: BaseMessage) -> str:
    """Text of a message: `content` is a string, or a list of blocks (Anthropic)."""
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


async def call_with_retries(
    model: BaseChatModel,
    messages: list[BaseMessage],
    *,
    agent: str,
    allow_empty: bool = False,
    stream: bool = True,
    retry: bool = True,
) -> AIMessage:
    """`model.ainvoke` tagged by agent (the tag and the metadata go up to the cost callbacks
    and to the runner's `messages` mode), retried on a transient error.

    An empty reply (GLM: reasoning only, empty `content`) is retried the same way, unless
    `allow_empty` (the caller then handles it itself). `stream=False`: the reply is not
    streamed token by token (LangGraph's `nostream` tag), for raw JSON for example.
    """
    tags = [f"agent:{agent}"] if stream else [f"agent:{agent}", TAG_NOSTREAM]
    chat = model.with_config(metadata={"agent": agent}, tags=tags)
    deadline = _deadline(model)
    attempts = len(RETRY_DELAYS_S) + 1 if retry else 1
    for attempt in range(attempts):
        last = attempt == attempts - 1
        try:
            async with asyncio.timeout(deadline):  # total deadline (`None`: none)
                reply = await chat.ainvoke(messages)
        except Exception as exc:
            if last or not is_transient(exc):
                if (readable := _readable(exc, model, agent)) is None:
                    raise
                raise readable from None  # no provider message or body in the chain
            logger.warning(
                "LLM call retried: agent %s, attempt %d/%d, %s",
                agent,
                attempt + 1,
                attempts,
                type(exc).__name__,
            )
        else:
            text = message_text(reply)
            if allow_empty or text.strip() or reply.tool_calls:
                return reply
            if last:
                raise AppError(
                    "llm_empty_reply",
                    f"The {agent} agent returned an empty reply.",
                    502,
                    {"agent": agent},
                )
        await _sleep(RETRY_DELAYS_S[attempt])
    raise AssertionError("unreachable")  # pragma: no cover


def _deadline(model: BaseChatModel) -> float | None:
    """Total deadline of a call, set by the factory (`CALL_DEADLINE_KEY`); the SDK's timeout
    only bounds the wait for each chunk of a streamed reply (check 5.18)."""
    value = (model.metadata or {}).get(CALL_DEADLINE_KEY)
    return float(value) if isinstance(value, int | float) and value > 0 else None


def _readable(exc: Exception, model: BaseChatModel, agent: str) -> AppError | None:
    """Provider failure -> readable `AppError` (key refused, credit exhausted, limit, service
    unavailable, timeout) instead of the generic "unexpected error"; `None` for any other
    exception. Log: agent, provider and exception type, never its text."""
    metadata = model.metadata or {}
    provider = metadata.get("tremplin_provider")
    label = metadata.get("tremplin_provider_label") or "The provider"
    described = describe_provider_error(exc, provider=provider, label=str(label))
    if described is not None:
        logger.warning(
            "LLM call failed: agent %s, provider %s, %s (%s)",
            agent,
            provider or "unknown",
            type(exc).__name__,
            described.code,
        )
    return described


async def invoke_agent(
    model: BaseChatModel,
    messages: list[BaseMessage],
    *,
    agent: str,
    step: str,
    intent: str,
    expose_reply: bool = True,
) -> AIMessage:
    """Announces the intent (`agent.started`), calls the model (live tokens through the
    runner's `messages` mode), then emits the final text (`agent.message`)."""
    emit("agent.started", {"step": step, "intent": intent}, agent=agent)
    reply = await call_with_retries(model, messages, agent=agent, stream=expose_reply)
    if expose_reply:
        emit(
            "agent.message",
            {"message_id": reply.id or f"{agent}-{step}", "text": message_text(reply)},
            agent=agent,
        )
    return reply


def node_timeout(seconds: float = NODE_TIMEOUT_S) -> Callable[[F], F]:
    """Async node decorator: beyond `seconds`, `AppError("node_timeout")`."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limit = asyncio.timeout(seconds)
            try:
                async with limit:
                    return await func(*args, **kwargs)
            except TimeoutError:
                if not limit.expired():
                    raise  # a timeout raised by the node itself, not our cap
                raise AppError(
                    "node_timeout",
                    f"The {func.__name__} step exceeded {seconds:g} seconds.",
                    504,
                    {"node": func.__name__, "seconds": seconds},
                ) from None

        return cast(F, wrapper)

    return decorator
