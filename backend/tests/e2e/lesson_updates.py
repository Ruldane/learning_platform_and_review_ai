"""Recette locale de la veille et du circuit de révision P11."""

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.features.lesson_updates.service.schedule import scan_user
from tests.agents.graphs.council_models import QUERY, URLS
from tests.agents.graphs.lesson_support import LessonModels
from tests.agents.graphs.web_support import document, result
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.lesson_updates.fixtures import CORRECTION, MARKER, RELEASE, seed_update
from tests.support.lessons import verifier_reply


def use_releases(app: FastAPI) -> None:
    models = LessonModels()
    models.when("verifier", MARKER, CORRECTION)
    models.when("verifier", "", verifier_reply(), verifier_reply())
    app.state.injected_chat_models = models
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            research = current.state.research.providers
            research.searxng.results[QUERY] = [result(url, "Document fictif") for url in URLS[:2]]
            for url in URLS[:2]:
                research.web.pages[url] = document(url)
            mirror = RELEASE + "?mirror=1"
            research.web.pages[mirror] = document(mirror)
            await seed_update(current)
            await scan_user(current.state.lessons, current.state.local_user_id)
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8801)
    parser.add_argument("--origin", default="http://127.0.0.1:5201")
    args = parser.parse_args()
    data_dir = prepare_data_dir(args.data_dir)
    settings = e2e_settings(data_dir, origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings)
    use_releases(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
