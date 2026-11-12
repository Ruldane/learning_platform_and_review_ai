"""Modèles scriptés du parcours de bout en bout (SPEC 18.2) : un `ChatModelSource` sans réseau qui
rend, pour chaque agent, la réponse suivante de SA file. Les sessions du Conseil, du programme et
des leçons se suivent ou tournent en même temps sans ordre global ; seul l'ordre des appels d'un
même agent compte.

Une réponse est un texte ou une fonction des messages reçus (identifiants lus dans le prompt,
leçon au titre du module…). File épuisée : `RuntimeError` qui nomme l'agent, jamais le contenu
des messages. `delays` : attente avant chaque réponse d'un agent (le parcours Playwright a le temps
d'écrire pendant un tour)."""

import asyncio
import itertools
from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.providers.llm.base import Tier

type Reply = str | Callable[[Sequence[BaseMessage]], str]

MODEL_NAME = "modele-scripte"


def _words(messages: Sequence[BaseMessage]) -> int:
    return sum(len(str(m.content).split()) for m in messages)


class ScriptedModels:
    """`ChatModelSource` : une file de réponses par agent (`scripts`), servies dans l'ordre."""

    def __init__(
        self, scripts: Mapping[str, Sequence[Reply]], *, delays: Mapping[str, float] | None = None
    ) -> None:
        self._queues: dict[str, list[Reply]] = {a: list(r) for a, r in scripts.items()}
        self._delays = dict(delays or {})
        self._ids = itertools.count(1)
        self.served: dict[str, int] = {}

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        meta = {"tremplin_provider": "fake", "tremplin_model": MODEL_NAME}
        return ScriptedChat(source=self, agent=agent or "", metadata=meta)

    def remaining(self) -> dict[str, int]:
        """Réponses pas encore servies, par agent (les agents à file vide sont omis)."""
        return {agent: len(queue) for agent, queue in self._queues.items() if queue}

    async def wait(self, agent: str) -> None:
        if delay := self._delays.get(agent, 0.0):
            await asyncio.sleep(delay)

    def next_reply(self, agent: str, messages: Sequence[BaseMessage]) -> tuple[str, str]:
        """`(id du message, texte)` de la réponse suivante de `agent`."""
        queue = self._queues.get(agent, [])
        if not queue:
            raise RuntimeError(f"Modèles scriptés : plus de réponse prévue pour l'agent {agent}.")
        reply = queue.pop(0)
        text = reply if isinstance(reply, str) else reply(messages)
        self.served[agent] = self.served.get(agent, 0) + 1
        return f"scripted-{next(self._ids)}", text


def _usage(messages: Sequence[BaseMessage], text: str) -> UsageMetadata:
    tokens_in, tokens_out = _words(messages), len(text.split())
    return UsageMetadata(
        input_tokens=tokens_in, output_tokens=tokens_out, total_tokens=tokens_in + tokens_out
    )


class ScriptedChat(BaseChatModel):
    """Modèle d'un agent : chaque appel (direct ou diffusé) prend UNE réponse de sa file. La
    diffusion se fait ligne par ligne (une leçon de 1 500 mots ne fait pas 1 500 événements)."""

    source: Any  # ScriptedModels (pydantic ne valide pas la classe)
    agent: str

    @property
    def _llm_type(self) -> str:
        return "tremplin-scripted-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        message_id, text = self.source.next_reply(self.agent, messages)
        message = AIMessage(content=text, id=message_id, usage_metadata=_usage(messages, text))
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        await self.source.wait(self.agent)
        return self._generate(messages)

    def _chunks(self, messages: list[BaseMessage]) -> Iterator[ChatGenerationChunk]:
        message_id, text = self.source.next_reply(self.agent, messages)
        lines = text.split("\n")
        for position, line in enumerate(lines):
            last = position == len(lines) - 1
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=line if last else line + "\n",
                    id=message_id,
                    usage_metadata=_usage(messages, text) if last else None,
                    chunk_position="last" if last else None,
                )
            )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        await self.source.wait(self.agent)
        for chunk in self._chunks(messages):
            if run_manager:
                await run_manager.on_llm_new_token(str(chunk.message.content), chunk=chunk)
            yield chunk
