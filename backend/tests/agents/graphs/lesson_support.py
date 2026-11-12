"""Matériel des tests du parcours `lesson_factory` : le runner de `make_web_runner` (vraie mémoire,
vraie recherche sur de faux moteurs) avec des faux modèles par agent (`LessonModels`, sur
`CouncilModels`) et le faux port des leçons (`FakeLessonStore`). Aucun réseau ni LLM réel."""

import asyncio
import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk

from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from app.providers.llm.base import Tier
from app.providers.llm.fake import _Script
from app.providers.search.base import SearchResult
from app.providers.web.base import WebDocument
from tests.agents.graphs.council_models import (
    QUERY,
    URLS,
    CouncilChat,
    CouncilModels,
    Rule,
    prompt_text,
)
from tests.agents.graphs.web_support import SCORE_82, MakeWeb, Web
from tests.agents.runtime.runner_helpers import all_events, get_session
from tests.support.lessons import (
    MODULE_ID,
    PROGRAM_ID,
    FakeLessonStore,
    lesson_markdown,
)

PATIENCE_S = 60
RESOURCES_MARKER = "Tâche : choisir les ressources d'apprentissage"
NO_CLAIM = json.dumps({"unsupported": []})
GOOD_LESSON = lesson_markdown(1500, urls=(URLS[0], URLS[1]))
_SOURCE_ID = re.compile(r"source_id : (\S+) \(note")

type Picker = Callable[[list[str]], list[dict[str, Any]]]


def pick(source_id: str, kind: str = "article") -> dict[str, Any]:
    return {
        "source_id": source_id,
        "type": kind,
        "duration_minutes": 30,
        "level": "debutant",
        "reason": "Explique bien le sujet du module.",
    }


def first_four(ids: list[str]) -> list[dict[str, Any]]:
    return [pick(sid) for sid in ids[:4]]


def claims(*items: str) -> str:
    return json.dumps({"unsupported": list(items)})


class LessonChat(CouncilChat):
    """Diffuse par lignes et non mot à mot : une leçon de 1 500 mots ferait 1 500 événements."""

    def _chunks(self, messages: list[BaseMessage]) -> Iterator[ChatGenerationChunk]:
        index, text, usage = self.source.reply(self.agent, messages)
        lines = text.split(chr(10))
        for position, line in enumerate(lines):
            last = position == len(lines) - 1
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=line if last else line + chr(10),
                    id=f"fake-{index}",
                    usage_metadata=usage if last else None,
                    chunk_position="last" if last else None,
                )
            )


@dataclass
class LessonModels(CouncilModels):
    """Faux modèles du Conseil, plus le choix des ressources : les `source_id` sont ceux du
    prompt (ils sont créés par la base), `picker` les transforme en choix du modèle."""

    picker: Picker = first_four

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        meta = {"tremplin_provider": "fake", "tremplin_model": "modele-test"}
        return LessonChat(script=_Script([], []), metadata=meta, agent=agent or "", source=self)

    def reply(self, agent: str, messages: list[BaseMessage]) -> Any:
        prompt = prompt_text(messages)
        if agent == "scout" and RESOURCES_MARKER in prompt:
            ids = _SOURCE_ID.findall(prompt)
            text = json.dumps({"resources": self.picker(ids)})
            self.rules.insert(0, Rule("scout", RESOURCES_MARKER, [text]))
        return super().reply(agent, messages)


@dataclass
class Lesson:
    runner: SessionRunner
    web: Web
    store: FakeLessonStore
    models: LessonModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        """Attend l'état : une leçon de 1 500 mots est diffusée mot à mot (un événement chacun),
        ce qui prend plus que le délai des autres parcours."""
        async with asyncio.timeout(PATIENCE_S):
            while (
                row := await get_session(self.web.factory, self.user_id, self.sid)
            ).status != status:
                assert row.status != "failed" or status == "failed", row.error
                await asyncio.sleep(0.01)
        return row

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.web.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    def prompts_of(self, agent: str) -> list[str]:
        return [call.prompt for call in self.models.calls if call.agent == agent]

    @property
    def writer_calls(self) -> int:
        return len(self.prompts_of("writer"))

    def prompt_of_writer(self, number: int) -> str:
        """Prompt du `number`-ième appel du Rédacteur (à partir de 1)."""
        return self.prompts_of("writer")[number - 1]

    async def wait_published(self) -> None:
        async with asyncio.timeout(PATIENCE_S):
            while not self.store.publish_calls:
                await asyncio.sleep(0.01)


type MakeLesson = Callable[..., Awaitable[Lesson]]


def script_lesson_web(
    web: Web, *, pages: int, seeds: tuple[str, ...], text: str = "Texte de la page."
) -> None:
    web.search.results[QUERY] = [
        SearchResult(title=f"Titre {n}", url=u, snippet="extrait", engine="fake", published=None)
        for n, u in enumerate(URLS[:pages])
    ]
    for n, url in enumerate([*URLS[:pages], *seeds]):
        web.reader.pages[url] = WebDocument(
            url, f"Article {n}", text, "Ada Lovelace", "2026-01-02", "fr", None
        )


@pytest.fixture
async def make_lesson_runner(make_web_runner: MakeWeb, user_id: str) -> AsyncIterator[MakeLesson]:
    """`make(...)` démarre `lesson_factory` sur le module du faux port. `writer`, `verifier` :
    réponses scriptées (puis la bonne leçon / « rien à signaler ») ; `scores` : notes des pages
    (puis 82) ; `picker` : choix des ressources ; `pages` : résultats de recherche lisibles ;
    `seeds` : adresses de départ du module ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même port, mêmes faux moteurs)."""
    store = FakeLessonStore()

    async def make(
        *,
        writer: list[str] | None = None,
        verifier: list[str] | None = None,
        scores: list[str] | None = None,
        picker: Picker = first_four,
        pages: int = 5,
        seeds: tuple[str, ...] = (),
        page_text: str = "Texte de la page.",
        sid: str | None = None,
        module_id: str = MODULE_ID,
    ) -> Lesson:
        models = LessonModels(picker=picker)
        models.when("scout", "Note cette source.", *(scores or []), *[SCORE_82] * 20)
        models.when("writer", "", *(writer or []), *[GOOD_LESSON] * 20)
        models.when("verifier", "", *(verifier or []), *[NO_CLAIM] * 20)
        web = await make_web_runner([], models=models, lessons=store)
        script_lesson_web(web, pages=pages, seeds=seeds, text=page_text)
        if (user_id, module_id) not in store.briefs:
            store.add_module(user_id, module_id=module_id, seeds=seeds)
        lesson = Lesson(web.runner, web, store, models, user_id)
        body = {"program_id": PROGRAM_ID, "module_id": module_id}
        lesson.sid = sid or await web.runner.start(
            user_id, "lesson_factory", body, "program", PROGRAM_ID
        )
        return lesson

    yield make
