"""The IDE's OpenAI access. Sandbox code only sees the response text."""

import asyncio
from typing import Literal, Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.core.played import inherit_source
from app.features.ide.gateway_repository import reserve
from app.features.ide.repository import RunRepository
from app.features.settings.service import SettingsService
from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.limits import with_output_limit

DAILY_CAP = 10_000
MAX_REQUEST_BYTES = 16_384
MAX_REPLY_BYTES = 16_384
_OPENAI_TIERS: tuple[Tier, ...] = ("rapide", "standard", "fort")
_MESSAGES = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}


def _part_text(part: object) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict) and part.get("type") in ("text", "output_text"):
        value = part.get("text")
        if isinstance(value, str):
            return value
    return ""


class _Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=8_192)


class _Completion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    model: str = Field(min_length=1, max_length=120)
    messages: list[_Message] = Field(min_length=1, max_length=16)
    max_tokens: int = Field(default=256, ge=1, le=1024)

    def reservation(self) -> int:
        return sum(len(msg.content.encode()) + 12 for msg in self.messages) + self.max_tokens


class Models(Protocol):
    async def resolve(self, user_id: str, tier: Tier) -> ModelChoice: ...

    async def get_chat_model(self, user_id: str, tier: Tier) -> BaseChatModel: ...


class ModelGateway:
    def __init__(
        self, factory: async_sessionmaker[AsyncSession], models: Models, *, day_cap: int = DAILY_CAP
    ) -> None:
        self._factory = factory
        self._models = models
        self._day_cap = day_cap

    async def allowed_run(self, user_id: str, run_id: str) -> bool:
        async with self._factory() as db:
            row = await RunRepository(db, user_id).get_fresh(run_id)
            return bool(
                row is not None
                and row.origin == "app"
                and row.status == "running"
                and row.kind in {"run", "terminal", "notebook"}
            )

    async def _tier(self, user_id: str, name: str) -> Tier:
        for tier in _OPENAI_TIERS:
            choice = await self._models.resolve(user_id, tier)
            if choice.provider == "openai" and choice.model == name:
                return tier
        raise AppError("gateway_model_refused", "This OpenAI model is not configured.", 422)

    async def _reserve(self, user_id: str, amount: int) -> None:
        async with self._factory() as db:
            settings = await SettingsService(db, user_id).get()
            day = local_today(user_zone(settings.timezone)).isoformat()
            if not await reserve(db, user_id, day, amount, self._day_cap):
                raise AppError("gateway_budget_exhausted", "Daily budget exhausted.", 429)
            await db.commit()  # A provider outage cannot let the budget be exceeded.

    async def complete(self, user_id: str, payload: object) -> str:
        try:
            request = _Completion.model_validate(payload)
            amount = request.reservation()
        except (ValidationError, UnicodeEncodeError):
            raise AppError("gateway_request_invalid", "Invalid model request.", 422) from None
        if amount > MAX_REQUEST_BYTES:
            raise AppError("gateway_request_invalid", "Model request too large.", 422)
        with inherit_source(user_id, None, "openai"):
            tier = await self._tier(user_id, request.model)
            model = await self._models.get_chat_model(user_id, tier)
            await self._reserve(user_id, amount)
            messages = [
                _MESSAGES[message.role](content=message.content) for message in request.messages
            ]
            async with asyncio.timeout(8):
                response = await with_output_limit(model, request.max_tokens).ainvoke(messages)
        output = response.content
        if isinstance(output, list):
            output = "".join(map(_part_text, output))
        return output.encode()[:MAX_REPLY_BYTES].decode(errors="ignore")
