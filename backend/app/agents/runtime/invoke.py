"""Appel d'un modèle depuis un nœud : événements d'intention, nouveaux essais avec attente
croissante sur les erreurs du fournisseur, plafond de 120 s par nœud (SPEC 9.6, D44).

Les modèles de la fabrique sont construits sans nouveaux essais du SDK (`max_retries=0`) : c'est
ici, et ici seulement, qu'un appel est retenté.
"""

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

from app.agents.runtime.emit import emit
from app.core.errors import AppError
from app.providers.llm.errors import is_transient

NODE_TIMEOUT_S = 120
RETRY_DELAYS_S = (1.0, 2.0, 4.0)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)  # point d'accroche des tests


def message_text(message: BaseMessage) -> str:
    """Texte d'un message : `content` est une chaîne, ou une liste de blocs (Anthropic)."""
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
    model: BaseChatModel, messages: list[BaseMessage], *, agent: str, allow_empty: bool = False
) -> AIMessage:
    """`model.ainvoke` étiqueté par agent (l'étiquette et les métadonnées remontent aux
    callbacks du coût et au mode `messages` du runner), retenté sur erreur transitoire.

    Une réponse vide (GLM : réflexion seule, `content` vide) est retentée de même, sauf si
    `allow_empty` (l'appelant la traite alors lui-même).
    """
    chat = model.with_config(metadata={"agent": agent}, tags=[f"agent:{agent}"])
    for attempt in range(len(RETRY_DELAYS_S) + 1):
        last = attempt == len(RETRY_DELAYS_S)
        try:
            reply = await chat.ainvoke(messages)
        except Exception as exc:
            if last or not is_transient(exc):
                raise
        else:
            text = message_text(reply)
            if allow_empty or text.strip() or reply.tool_calls:
                return reply
            if last:
                raise AppError(
                    "llm_empty_reply",
                    f"L'agent {agent} a renvoyé une réponse vide.",
                    502,
                    {"agent": agent},
                )
        await _sleep(RETRY_DELAYS_S[attempt])
    raise AssertionError("inatteignable")  # pragma: no cover


async def invoke_agent(
    model: BaseChatModel, messages: list[BaseMessage], *, agent: str, step: str, intent: str
) -> AIMessage:
    """Annonce l'intention (`agent.started`), appelle le modèle (tokens en direct par le mode
    `messages` du runner), puis émet le texte final (`agent.message`)."""
    emit("agent.started", {"step": step, "intent": intent}, agent=agent)
    reply = await call_with_retries(model, messages, agent=agent)
    emit(
        "agent.message",
        {"message_id": reply.id or f"{agent}-{step}", "text": message_text(reply)},
        agent=agent,
    )
    return reply


def node_timeout(seconds: float = NODE_TIMEOUT_S) -> Callable[[F], F]:
    """Décorateur de nœud asynchrone : au-delà de `seconds`, `AppError("node_timeout")`."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            limit = asyncio.timeout(seconds)
            try:
                async with limit:
                    return await func(*args, **kwargs)
            except TimeoutError:
                if not limit.expired():
                    raise  # un délai levé par le nœud lui-même, pas notre plafond
                raise AppError(
                    "node_timeout",
                    f"L'étape {func.__name__} a dépassé {seconds:g} secondes.",
                    504,
                    {"node": func.__name__, "seconds": seconds},
                ) from None

        return cast(F, wrapper)

    return decorator
