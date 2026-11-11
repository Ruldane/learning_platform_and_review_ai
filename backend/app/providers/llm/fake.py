"""Faux fournisseur LLM, sans réseau : tests de bout en bout et tests des graphes d'agents."""

from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.providers.llm.base import KeyTestResult


def _words(content: Any) -> int:
    if isinstance(content, str):
        return len(content.split())
    return sum(len(str(part.get("text", "")).split()) for part in content if isinstance(part, dict))


class _Script:
    """Réponses à rendre dans l'ordre et messages reçus, partagés par les modèles construits."""

    def __init__(self, responses: list[str], received: list[list[BaseMessage]]) -> None:
        self._responses = responses
        self.received = received
        self._calls = 0

    def next_reply(self, messages: list[BaseMessage]) -> tuple[str, UsageMetadata]:
        self.received.append(list(messages))
        if self._calls >= len(self._responses):
            raise RuntimeError("FakeLlmProvider : plus aucune réponse prévue pour cet appel.")
        reply = self._responses[self._calls]
        self._calls += 1
        tokens_in = sum(_words(m.content) for m in messages)
        tokens_out = len(reply.split())
        usage = UsageMetadata(
            input_tokens=tokens_in, output_tokens=tokens_out, total_tokens=tokens_in + tokens_out
        )
        return reply, usage


class FakeChatModel(BaseChatModel):
    script: _Script

    @property
    def _llm_type(self) -> str:
        return "tremplin-fake-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        reply, usage = self.script.next_reply(messages)
        message = AIMessage(content=reply, usage_metadata=usage)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _chunks(self, messages: list[BaseMessage]) -> Iterator[ChatGenerationChunk]:
        reply, usage = self.script.next_reply(messages)
        words = reply.split(" ")
        for index, word in enumerate(words):
            last = index == len(words) - 1
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=word if last else f"{word} ",
                    usage_metadata=usage if last else None,
                    chunk_position="last" if last else None,
                )
            )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        for chunk in self._chunks(messages):
            if run_manager:
                run_manager.on_llm_new_token(str(chunk.message.content), chunk=chunk)
            yield chunk

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for chunk in self._chunks(messages):
            if run_manager:
                await run_manager.on_llm_new_token(str(chunk.message.content), chunk=chunk)
            yield chunk


class FakeLlmProvider:
    name = "fake"
    label = "Faux fournisseur"

    def __init__(self, responses: list[str], *, valid_key: str = "fake-key") -> None:
        self.responses = responses
        self.valid_key = valid_key
        self.built: list[tuple[str, str]] = []
        self.base_urls: list[str | None] = []
        self.received: list[list[BaseMessage]] = []
        self._script = _Script(responses, self.received)

    def build(self, model: str, api_key: str, *, base_url: str | None = None) -> BaseChatModel:
        self.built.append((model, api_key))
        self.base_urls.append(base_url)
        return FakeChatModel(script=self._script)

    async def list_models(self, api_key: str) -> list[str] | None:
        return None

    async def test_key(self, api_key: str) -> KeyTestResult:
        if api_key == self.valid_key:
            return KeyTestResult(ok=True, message="Clé valide.")
        return KeyTestResult(ok=False, message="Clé refusée par le faux fournisseur.")
