"""Progression du téléchargement de `bge-m3` (P13) : Ollama est remplacé par `httpx.MockTransport`,
aucun appel réseau."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from app.providers.embeddings.ollama_pull import OllamaPullWatcher

BASE = "http://ollama:11434"
MODEL = "bge-m3"
SECRET_LINE = "https://registry.example.invalid/secret-path"


class FakeOllama:
    """Un Ollama de poche : `/api/tags` et `/api/pull` en flux, avec la liste des téléchargements.
    `lines` : les lignes du flux ; `gate` : tant que `hold`, le flux attend ce signal avant sa
    dernière ligne (le téléchargement reste « en cours »)."""

    def __init__(self, lines: list[dict[str, object]], *, present: bool = False) -> None:
        self.lines = lines
        self.present = present
        self.pulls: list[dict[str, object]] = []
        self.gate = asyncio.Event()
        self.hold = True
        self.down = False

    def _stream(self) -> AsyncIterator[bytes]:
        async def chunks() -> AsyncIterator[bytes]:
            for index, line in enumerate(self.lines):
                if self.hold and index == len(self.lines) - 1:
                    await self.gate.wait()
                yield (json.dumps(line) + "\n").encode()

        return chunks()

    async def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("injoignable")
        if request.url.path == "/api/tags":
            models = [{"name": "bge-m3:latest"}] if self.present else []
            return httpx.Response(200, json={"models": models})
        assert request.url.path == "/api/pull" and request.method == "POST"
        self.pulls.append(json.loads(request.content))
        return httpx.Response(
            200, headers={"content-type": "application/x-ndjson"}, content=self._stream()
        )


def watcher_for(
    ollama: FakeOllama, clock: Callable[[], float] | None = None
) -> tuple[OllamaPullWatcher, httpx.AsyncClient]:
    http = httpx.AsyncClient(transport=httpx.MockTransport(ollama.handle))
    if clock is None:
        return OllamaPullWatcher(BASE, MODEL, http), http
    return OllamaPullWatcher(BASE, MODEL, http, clock=clock), http


async def settle() -> None:
    for _ in range(30):
        await asyncio.sleep(0)


async def test_present_model_is_100() -> None:
    ollama = FakeOllama([], present=True)
    watcher, http = watcher_for(ollama)
    async with http:
        data = await watcher.progress()
    assert (data.model, data.present, data.percent) == (MODEL, True, 100)
    assert data.detail and ollama.pulls == []  # rien n'est téléchargé quand le modèle est là


async def test_progress_reports_percent_from_stream() -> None:
    ollama = FakeOllama(
        [
            {"status": "pulling manifest"},
            {"status": "pulling aaa", "digest": "sha256:aaa", "total": 1000, "completed": 250},
            {"status": "pulling aaa", "digest": "sha256:aaa", "total": 1000, "completed": 500},
            # un petit fichier fini ne remplace pas la progression du gros
            {"status": "pulling bbb", "digest": "sha256:bbb", "total": 10, "completed": 10},
            {"status": "success"},
        ]
    )
    watcher, http = watcher_for(ollama)
    async with http:
        first = await watcher.progress()  # lance le téléchargement
        assert first.percent is None and not first.present
        await settle()
        data = await watcher.progress()
        assert (data.present, data.percent) == (False, 50)
        assert "50" in data.detail and MODEL in data.detail
        assert ollama.pulls == [{"name": MODEL, "stream": True}]
        ollama.present = True
        ollama.gate.set()
        await settle()
        done = await watcher.progress()
    assert (done.present, done.percent) == (True, 100)


async def test_percent_never_reaches_100_before_the_model_is_present() -> None:
    ollama = FakeOllama(
        [{"status": "pulling a", "digest": "a", "total": 100, "completed": 100}, {"status": "ok"}]
    )
    watcher, http = watcher_for(ollama)
    async with http:
        await watcher.progress()
        await settle()
        data = await watcher.progress()
        ollama.gate.set()
    assert data.percent == 99 and not data.present


async def test_pull_started_once_for_concurrent_calls() -> None:
    ollama = FakeOllama([{"status": "pulling manifest"}, {"status": "success"}])
    watcher, http = watcher_for(ollama)
    async with http:
        results = await asyncio.gather(*(watcher.progress() for _ in range(8)))
        await settle()
        await watcher.progress()
        ollama.gate.set()
        await settle()
        await watcher.progress()  # fini, modèle encore absent : pas de second téléchargement
        await settle()
    assert len(ollama.pulls) == 1
    assert all(not r.present for r in results)


async def test_ollama_down_is_readable() -> None:
    ollama = FakeOllama([])
    ollama.down = True
    watcher, http = watcher_for(ollama)
    async with http:
        data = await watcher.progress()
    assert (data.present, data.percent, data.detail) == (False, None, "Ollama ne répond pas.")
    assert data.model == MODEL and ollama.pulls == []


async def test_ollama_error_status_is_readable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with http:
        data = await OllamaPullWatcher(BASE, MODEL, http).progress()
    assert not data.present and data.percent is None and data.detail == "Ollama ne répond pas."


async def test_failed_pull_is_retried_only_after_a_pause(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    ollama = FakeOllama([{"error": SECRET_LINE}])
    ollama.hold = False
    now = [1000.0]
    watcher, http = watcher_for(ollama, clock=lambda: now[0])
    async with http:
        await watcher.progress()
        await settle()
        again = await watcher.progress()  # échec tout frais : on attend
        assert len(ollama.pulls) == 1 and not again.present and again.percent is None
        assert "échoué" in again.detail
        now[0] += 3600
        await watcher.progress()
        await settle()
    assert len(ollama.pulls) == 2
    # le message de l'erreur d'Ollama n'est jamais journalisé : seulement sa nature
    assert SECRET_LINE not in " ".join(r.getMessage() for r in caplog.records)


async def test_pull_cut_short_is_a_failure_not_a_crash() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        raise httpx.ReadError("coupé")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with http:
        watcher = OllamaPullWatcher(BASE, MODEL, http)
        await watcher.progress()
        await settle()
        data = await watcher.progress()
    assert not data.present and "échoué" in data.detail


async def test_stream_closed_without_success_is_a_failure_then_retried() -> None:
    ollama = FakeOllama([{"status": "pulling manifest"}])  # le flux se ferme sans `success`
    ollama.hold = False
    now = [0.0]
    watcher, http = watcher_for(ollama, clock=lambda: now[0])
    async with http:
        await watcher.progress()
        await settle()
        data = await watcher.progress()
        assert data.percent is None and "échoué" in data.detail and len(ollama.pulls) == 1
        now[0] += 31
        await watcher.progress()
        await settle()
    assert len(ollama.pulls) == 2


async def test_finished_model_still_absent_is_pulled_again_later() -> None:
    ollama = FakeOllama([{"status": "pulling manifest"}, {"status": "success"}])
    ollama.hold = False
    now = [0.0]
    watcher, http = watcher_for(ollama, clock=lambda: now[0])
    async with http:
        await watcher.progress()
        await settle()
        waiting = await watcher.progress()  # fini, pas encore listé : 99, pas de second tirage
        assert waiting.percent == 99 and len(ollama.pulls) == 1
        now[0] += 31  # toujours absent (retiré, ou jamais arrivé) : on relance
        await watcher.progress()
        await settle()
    assert len(ollama.pulls) == 2


async def test_retry_delay_grows_then_is_capped_and_helps() -> None:
    ollama = FakeOllama([{"error": SECRET_LINE}])
    ollama.hold = False
    now = [0.0]
    watcher, http = watcher_for(ollama, clock=lambda: now[0])
    async with http:
        await watcher.progress()
        await settle()
        for index, delay in enumerate([30, 60, 120, 240, 300, 300], start=1):
            assert len(ollama.pulls) == index
            now[0] += delay - 1
            early = await watcher.progress()
            assert len(ollama.pulls) == index  # pas avant le délai
            assert "Ollama" in early.detail and SECRET_LINE not in early.detail
            now[0] += 1
            await watcher.progress()
            await settle()
    assert len(ollama.pulls) == 7


async def test_a_success_resets_the_retry_delay() -> None:
    ollama = FakeOllama([{"error": "x"}])
    ollama.hold = False
    now = [0.0]
    watcher, http = watcher_for(ollama, clock=lambda: now[0])
    async with http:
        for _ in range(3):  # trois échecs : le délai monte à 120 s
            await watcher.progress()
            await settle()
            now[0] += 1000
        ollama.lines = [{"status": "success"}]  # un tirage va au bout, modèle encore absent
        await watcher.progress()
        await settle()
        now[0] += 31
        ollama.lines = [{"error": "x"}]
        await watcher.progress()  # relancé après 31 s : la fin « réussie » n'allonge rien
        await settle()
        before = len(ollama.pulls)
        now[0] += 31  # un seul échec depuis la réussite : 30 s suffisent
        await watcher.progress()
        await settle()
    assert len(ollama.pulls) == before + 1


async def test_aclose_cancels_the_pull_without_logging_a_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    ollama = FakeOllama([{"status": "pulling manifest"}, {"status": "success"}])  # reste en cours
    watcher, http = watcher_for(ollama)
    async with http:
        before = len(asyncio.all_tasks())
        await watcher.progress()
        await settle()
        assert len(asyncio.all_tasks()) == before + 1
        await watcher.aclose()
        assert len(asyncio.all_tasks()) == before  # plus de tâche pendante
        await watcher.aclose()  # sans effet la seconde fois
    assert "échec" not in " ".join(r.getMessage() for r in caplog.records)
    assert all(r.levelno < logging.WARNING for r in caplog.records)


async def test_aclose_without_a_pull_is_harmless() -> None:
    watcher, http = watcher_for(FakeOllama([]))
    async with http:
        await watcher.aclose()
