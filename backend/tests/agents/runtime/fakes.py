"""Faux modèles de chat des tests du runtime (aucun réseau)."""

from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

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
