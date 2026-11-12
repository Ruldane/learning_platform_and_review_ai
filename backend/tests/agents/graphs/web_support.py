"""Matériel des tests du parcours `web_research` : vraie mémoire, vraie recherche web (base de
test) sur de faux moteurs, un faux lecteur de pages et un faux LLM. Aucun réseau."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from cryptography.fernet import Fernet
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.runner import SessionRunner
from app.core.security import Cipher
from app.db.models.accounts import User
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime
from app.features.research.service.gateway import AgentWebGateway
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.keys_service import DbKeyReader
from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeChatModel, FakeLlmProvider, _Script
from app.providers.search.base import SearchResult
from app.providers.search.fake import FakeSearch
from app.providers.web.base import UrlUnreadable, WebDocument
from tests.support.memory import FakeWebReader
from tests.support.research import fake_research_providers

type Factory = async_sessionmaker[AsyncSession]

PLAN = json.dumps(
    {
        "queries": [
            {"text": "attention multi-têtes", "lang": "fr"},
            {"text": "multi-head attention", "lang": "en"},
        ]
    }
)
URL_A = "https://docs.exemple.org/attention"
URL_B = "https://blog.exemple.fr/billet"
URL_C = "https://vide.exemple.fr/page"


def score(total_parts: tuple[int, int, int, int, int], reason: str = "Raison.") -> str:
    a, f, d, au, p = total_parts
    return json.dumps(
        {
            "authority": a,
            "freshness": f,
            "depth": d,
            "author": au,
            "pedagogy": p,
            "reason": reason,
            "summary": "Résumé de la page.",
        }
    )


SCORE_82 = score((25, 15, 15, 12, 15), "Documentation de référence.")
SCORE_41 = score((15, 8, 8, 5, 5), "Billet léger.")


def result(url: str, title: str) -> SearchResult:
    return SearchResult(title=title, url=url, snippet="extrait", engine="fake", published=None)


def document(url: str, *, title: str = "Attention", text: str = "Texte de la page.") -> WebDocument:
    return WebDocument(url, title, text, "Ada Lovelace", "2025-01-02", "fr", None)


class GatedChat(FakeChatModel):
    """Faux modèle qui se fige (jusqu'à l'annulation de la tâche) dès `block_from` réponses
    rendues : simule un arrêt du back en plein milieu d'un nœud."""

    block_from: int = 99

    async def _agenerate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> Any:
        if self.script._calls >= self.block_from:  # noqa: SLF001
            await asyncio.Event().wait()
        return self._generate(messages)


class GatedModels:
    """`ChatModelSource` sur `GatedChat`."""

    def __init__(self, replies: list[str], block_from: int) -> None:
        self.received: list[list[BaseMessage]] = []
        self._script = _Script(replies, self.received)
        self._block_from = block_from

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        meta = {"tremplin_provider": "fake", "tremplin_model": "modele-test"}
        return GatedChat(script=self._script, metadata=meta, block_from=self._block_from)


def script_web(web: "Web", *, urls: tuple[str, ...] = (URL_A, URL_B)) -> None:
    """Deux requêtes : la première rend A et B, la seconde C (illisible)."""
    web.search.results["attention multi-têtes"] = [result(u, f"Titre {u}") for u in urls]
    web.search.results["multi-head attention"] = [result(URL_C, "Page vide")]
    web.reader.pages[URL_A] = document(URL_A, title="Doc A")
    web.reader.pages[URL_B] = document(URL_B, title="Billet B")
    web.reader.pages[URL_C] = UrlUnreadable()


@dataclass
class Web:
    runner: SessionRunner
    fake: FakeLlmProvider | None
    memory: MemoryRuntime
    factory: Factory
    search: FakeSearch
    reader: FakeWebReader
    research: ResearchRuntime
    gateway: AgentWebGateway
    memory_gateway: AgentMemoryGateway


type MakeWeb = Callable[..., Awaitable[Web]]


async def add_users(factory: Factory, *user_ids: str) -> None:
    async with factory() as db:
        for number, uid in enumerate(user_ids):
            db.add(User(id=uid, user_id=uid, name="Jane Doé", email=f"jane{number}@x.fr"))
        await db.commit()


async def session_status(factory: Factory, user_id: str, sid: str) -> str:
    async with factory() as db:
        row = await SessionRepository(db, user_id).get(sid)
    assert row is not None
    return row.status


def research_runtime(
    factory: Factory, search: FakeSearch, reader: FakeWebReader
) -> ResearchRuntime:
    """Recherche web réelle (base de test), faux moteurs et lecteur, sans clé Brave."""
    keys = DbKeyReader(factory, Cipher(Fernet.generate_key()), {})
    return ResearchRuntime(factory, fake_research_providers(reader, searxng=search), keys)
