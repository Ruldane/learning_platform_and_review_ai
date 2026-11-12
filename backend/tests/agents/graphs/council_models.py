"""Faux modèles du Conseil, sans réseau : un `ChatModelSource` qui sait quel agent l'appelle.

Chaque appel rend, dans l'ordre : la première règle (`when`) de l'agent dont le marqueur figure
dans le prompt, sinon la prochaine réponse du script commun (cadrage, recherche), sinon la
réponse par défaut de l'agent pour cette tâche (une prise de parole conforme aux règles 9.3, un
tableau valable, deux propositions…). Les réponses portent l'id `fake-<n>` (n : rang de l'appel),
qui devient le `message_id` de `agent.message` : `prompt_of` retrouve ainsi le prompt d'un
message. `hooks` s'exécutent avant chaque réponse ; `block` fige un appel (arrêt du back)."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeChatModel, _Script
from tests.agents.graphs.web_support import SCORE_82

QUERY = "ai product engineer"
PLAN = json.dumps({"queries": [{"text": QUERY, "lang": "fr"}]})
PAGE_COUNT = 9
URLS = [f"https://site{n}.exemple.org/article" for n in range(PAGE_COUNT)]
ADA_URL = URLS[0]
PEOPLE = json.dumps(
    {
        "people": [
            {"name": "Ada Lovelace", "role": "Ingénieure IA", "urls": [ADA_URL, URLS[1]]},
            {"name": "Inventée", "role": "Personne", "urls": ["https://invente.exemple/x"]},
        ]
    }
)
DEBATERS = ("strategist", "practitioner", "scout", "skeptic")
SPEECH = {
    "strategist": "January, je réponds au Praticien : commençons par les bases [1].",
    "practitioner": "Je rejoins le Stratège et January : un projet concret dès la semaine 2 [1].",
    "scout": "Les sources donnent raison au Sceptique et à January sur la charge [1].",
    "skeptic": "Je réponds à l'Éclaireur et à January : le budget est serré [1].\n"
    "Objection : trop de notions pour dix heures par semaine.",
}
ORDER = json.dumps({"order": list(DEBATERS), "intent": "Quel socle pour commencer ?"})
REVIEW = json.dumps({"stable": False, "summary": "Les positions bougent encore."})
STABLE = json.dumps({"stable": True, "summary": "Les positions ne bougent plus."})
BOARD = json.dumps(
    {"title": "Carte du domaine", "mermaid": 'flowchart TD\nA["Bases"] --> B["Projet"]'}
)
MINUTES = "Le Conseil s'accorde sur un socle puis un projet [1]."


def proposal(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "promise": "Construire des produits avec des LLM.",
        "duration_weeks": 8,
        "weekly_hours": 8,
        "skills": ["Python", "API de LLM"],
        "final_project": "Un assistant documentaire complet.",
        "tradeoffs": ["Peu de théorie."],
    }


PROPOSALS = json.dumps({"proposals": [proposal("Parcours pratique"), proposal("Parcours socle")]})
_DEFAULTS: list[tuple[str, str, str]] = [
    ("moderator", "Prépare les questions de cadrage.", json.dumps({"questions": []})),
    ("moderator", "Fixe l'ordre de parole du tour.", ORDER),
    ("moderator", "Fais le point du tour.", REVIEW),
    ("scout", "Prépare les requêtes de recherche.", PLAN),
    ("scout", "Note cette source.", SCORE_82),
    ("scout", "Repère les praticiens.", PEOPLE),
    ("scribe", "Dessine le tableau.", BOARD),
    ("scribe", "Rédige le compte rendu.", MINUTES),
    ("strategist", "Propose les parcours.", PROPOSALS),
]


def default_reply(agent: str, prompt: str) -> str:
    for who, marker, reply in _DEFAULTS:
        if who == agent and marker in prompt:
            return reply
    if agent in DEBATERS and "À toi de parler." in prompt:
        return SPEECH[agent]
    raise AssertionError(f"Aucune réponse prévue pour l'agent {agent}.")


def prompt_text(messages: list[BaseMessage]) -> str:
    return "\n".join(str(m.content) for m in messages)


@dataclass
class Call:
    index: int
    agent: str
    prompt: str
    reply: str


@dataclass
class Rule:
    agent: str
    marker: str
    replies: list[str]


type Hook = Callable[[str, str], Awaitable[None]]


@dataclass
class CouncilModels:
    script: list[str] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    hooks: list[Hook] = field(default_factory=list)
    block: Callable[[str, str], bool] | None = None
    blocked: int = 0

    def when(self, agent: str, marker: str, *replies: str) -> None:
        """Les prochains appels de `agent` dont le prompt contient `marker` rendent `replies`."""
        self.rules.append(Rule(agent, marker, list(replies)))

    def reply(self, agent: str, messages: list[BaseMessage]) -> tuple[int, str, UsageMetadata]:
        prompt = prompt_text(messages)
        rule = next(
            (r for r in self.rules if r.agent == agent and r.marker in prompt and r.replies), None
        )
        if rule is not None:
            text = rule.replies.pop(0)
        elif self.script:
            text = self.script.pop(0)
        else:
            text = default_reply(agent, prompt)
        self.calls.append(Call(len(self.calls), agent, prompt, text))
        tokens_in, tokens_out = len(prompt.split()), len(text.split())
        usage = UsageMetadata(
            input_tokens=tokens_in, output_tokens=tokens_out, total_tokens=tokens_in + tokens_out
        )
        return len(self.calls) - 1, text, usage

    async def before(self, agent: str, messages: list[BaseMessage]) -> None:
        prompt = prompt_text(messages)
        for hook in list(self.hooks):
            await hook(agent, prompt)
        if self.block is not None and self.block(agent, prompt):
            self.blocked += 1
            await asyncio.Event().wait()

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        meta = {"tremplin_provider": "fake", "tremplin_model": "modele-test"}
        return CouncilChat(script=_Script([], []), metadata=meta, agent=agent or "", source=self)


class CouncilChat(FakeChatModel):
    agent: str
    source: Any  # CouncilModels

    def _generate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> ChatResult:
        index, text, usage = self.source.reply(self.agent, messages)
        message = AIMessage(content=text, id=f"fake-{index}", usage_metadata=usage)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> Any:
        await self.source.before(self.agent, messages)
        return self._generate(messages)

    def _chunks(self, messages: list[BaseMessage]) -> Iterator[ChatGenerationChunk]:
        index, text, usage = self.source.reply(self.agent, messages)
        words = text.split(" ")
        for position, word in enumerate(words):
            last = position == len(words) - 1
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=word if last else f"{word} ",
                    id=f"fake-{index}",
                    usage_metadata=usage if last else None,
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
        await self.source.before(self.agent, messages)
        for chunk in self._chunks(messages):
            if run_manager:
                await run_manager.on_llm_new_token(str(chunk.message.content), chunk=chunk)
            yield chunk
