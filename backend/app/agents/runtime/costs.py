"""Suivi des coûts : chaque appel LLM est journalisé (`llm_calls`), cumulé dans la session, publié
en direct (`cost.updated`) ; un plafond de tokens par session coupe les appels suivants (9.6).

`CostTracker` est un callback LangChain asynchrone exécuté sur la boucle de l'appelant : le bus ne
sait pas publier depuis un autre fil (D42), un callback synchrone (exécuté dans un fil) est exclu.
"""

import json
import logging
import time
from collections.abc import Mapping
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

logger = logging.getLogger(__name__)

_UNKNOWN = "inconnu"


@dataclass(frozen=True)
class ModelPrice:
    input_per_mtok: float
    output_per_mtok: float


def load_prices(path: Path) -> dict[str, ModelPrice]:
    """Table des prix (USD par million de tokens) ; `ValueError` si une entrée est mal formée."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    prices: dict[str, ModelPrice] = {}
    for model, entry in raw.items():
        try:
            prices[model] = ModelPrice(
                float(entry["input_per_mtok"]), float(entry["output_per_mtok"])
            )
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Prix mal formé pour le modèle {model!r}") from None
    return prices


def estimate_cost(
    model: str, tokens_in: int, tokens_out: int, prices: Mapping[str, ModelPrice]
) -> float:
    """Coût estimé en USD ; 0.0 pour un modèle absent de la table."""
    price = prices.get(model)
    if price is None:
        return 0.0
    return (tokens_in * price.input_per_mtok + tokens_out * price.output_per_mtok) / 1_000_000


class TokenBudgetExceeded(AppError):
    def __init__(self, cap_tokens: int) -> None:
        super().__init__(
            "token_cap_reached",
            f"Plafond de {cap_tokens} tokens atteint pour cette session.",
            400,
            {"cap_tokens": cap_tokens},
        )


@dataclass(frozen=True)
class _CallStart:
    started: float
    agent: str | None
    provider: str
    model: str


def _usage(response: LLMResult) -> tuple[int, int]:
    """Tokens `(entrée, sortie)` du dernier message généré, `(0, 0)` si le modèle n'en donne pas."""
    for generations in reversed(response.generations):
        for generation in reversed(generations):
            usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
            if usage:
                return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    return 0, 0


class CostTracker(AsyncCallbackHandler):
    raise_error = True  # sans cela, TokenBudgetExceeded serait avalée par LangChain
    # Pas `run_inline` : un gestionnaire « en ligne » qui lève laisse les coroutines des autres
    # gestionnaires jamais attendues (langchain_core, `on_chat_model_start`) ; regroupé avec eux
    # par `asyncio.gather`, il s'exécute toujours sur la boucle de l'appelant (D42, D46).
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

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Refuse l'appel si le plafond de la session est atteint, sinon mémorise son départ.

        Provider et modèle : métadonnées `tremplin_*` posées par les fournisseurs, à défaut les
        `ls_provider` / `ls_model_name` que LangChain déduit du modèle.
        """
        async with self._factory() as db:
            session = await SessionRepository(db, self._user_id).get(self._session_id)
        if session is not None and session.tokens_in + session.tokens_out >= self._cap:
            raise TokenBudgetExceeded(self._cap)
        meta = metadata or {}
        self._calls[run_id] = _CallStart(
            started=time.monotonic(),
            agent=meta.get("agent"),
            provider=str(meta.get("tremplin_provider") or meta.get("ls_provider") or _UNKNOWN),
            model=str(meta.get("tremplin_model") or meta.get("ls_model_name") or _UNKNOWN),
        )

    async def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._calls.pop(run_id, None)

    async def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        start = self._calls.pop(run_id, None)
        if start is None:
            return
        try:
            await self._record(start, *_usage(response))
        except Exception:  # la comptabilité ne doit jamais faire échouer la réponse du modèle
            logger.exception("Suivi des coûts impossible pour la session %s", self._session_id)

    async def _record(self, start: _CallStart, tokens_in: int, tokens_out: int) -> None:
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
