"""Le code exécuté obtient une réponse bornée sans accès au fournisseur."""

import pytest
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.features.ide.repository import RunRepository
from app.features.ide.service.model_gateway import ModelGateway
from app.features.ide.service.model_socket import _complete
from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.fake import FakeLlmProvider


class Models:
    def __init__(self) -> None:
        self.provider = FakeLlmProvider(["une réponse fictive", "autre réponse"])

    async def resolve(self, user_id: str, tier: Tier) -> ModelChoice:
        return ModelChoice(provider="openai", model=f"fictif-{tier}")

    async def get_chat_model(self, user_id: str, tier: Tier) -> BaseChatModel:
        return self.provider.build(f"fictif-{tier}", "clé fictive", base_url=None)


async def test_gateway_validates_model_and_reserves_budget_before_invoking(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    models = Models()
    gateway = ModelGateway(db_session_factory, models, day_cap=64)
    ask = {
        "model": "fictif-fast",
        "messages": [{"role": "user", "content": "Bonjour"}],
        "max_tokens": 32,
    }
    with pytest.raises(AppError) as rejected:
        await gateway.complete("compte-un", {**ask, "model": "modèle non configuré"})
    assert rejected.value.code == "gateway_model_refused"
    assert not models.provider.received

    result = await gateway.complete("compte-un", ask)
    assert result == "une réponse fictive"
    with pytest.raises(AppError) as exhausted:
        await gateway.complete("compte-un", ask)
    assert exhausted.value.code == "gateway_budget_exhausted"
    assert len(models.provider.received) == 1
    assert await gateway.complete("compte-deux", ask) == "autre réponse"


async def test_gateway_only_accepts_an_owned_running_interface_job(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    models = Models()
    gateway = ModelGateway(db_session_factory, models)
    async with db_session_factory() as db:
        row = await RunRepository(db, "propriétaire").add(
            session_id="session-fictive", kind="terminal"
        )
        await db.commit()
    request = {"model": "fictif-fast", "messages": [{"role": "user", "content": "Salut"}]}
    envelope = {"run_id": row.id, "request": request}
    with pytest.raises(AppError) as refused:
        await _complete(gateway, {**envelope, "user_id": "autre-compte"})
    assert refused.value.code == "gateway_run_refused"
    assert models.provider.received == []
    assert (
        await _complete(gateway, {**envelope, "user_id": "propriétaire"}) == "une réponse fictive"
    )
