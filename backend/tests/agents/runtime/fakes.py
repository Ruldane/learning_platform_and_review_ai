"""Faux modèles de chat des tests du runtime (aucun réseau)."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.providers.llm.fake import FakeLlmProvider


class FlakyModel(BaseChatModel):
    """Échoue `fail_times` fois avec `exc`, puis répond `reply` ; `calls` compte les appels."""

    fail_times: int = 0
    exc: BaseException = RuntimeError("panne")
    reply: str = "ok"
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "flaky"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        raise NotImplementedError

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exc
        message = AIMessage(content=self.reply)
        return ChatResult(generations=[ChatGeneration(message=message)])


def fake_model(replies: list[str]) -> tuple[BaseChatModel, FakeLlmProvider]:
    """Modèle du faux fournisseur qui répond `replies` dans l'ordre ; le fournisseur garde les
    messages reçus (`provider.received`)."""
    provider = FakeLlmProvider(replies)
    return provider.build("modele-test", "fake-key"), provider


class HangingStream(BaseChatModel):
    """Réponse en flux qui envoie `chunks` morceaux puis attend sans fin (`fail` : lève à la place
    d'attendre, comme un fournisseur qui coupe la réponse). `streaming=True` à la construction :
    LangChain diffuse alors l'appel (un `on_llm_new_token` par morceau) hors d'un graphe aussi."""

    streaming: bool = False
    chunks: int = 3
    fail: BaseException | None = None
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "hanging-stream"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        raise NotImplementedError

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        self.calls += 1
        for index in range(self.chunks):
            yield ChatGenerationChunk(message=AIMessageChunk(content=f"m{index} "))
        if self.fail is not None:
            raise self.fail
        await asyncio.Event().wait()
