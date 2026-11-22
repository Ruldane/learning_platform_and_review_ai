"""Article, modèle et résultat de cellule synthétiques pour la recette Du papier au code."""

import argparse
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.providers.sandbox.fake import FakeSandbox
from app.providers.web.base import WebDocument
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.support.memory import FakeWebReader

URL = "https://articles.exemple.org/regression"
TITLE = "Mesurer une pente sur des points"
QUOTE = "L'expérience de démonstration obtient une pente de 2,0."
MATERIAL = (
    "La régression estime la pente qui décrit l'effet d'une variable sur une mesure. "
    "Trois points de la forme y = 2x forment une série synthétique parfaitement alignée. " + QUOTE
)
RESULT = "La pente estimée vaut 2,0 sur les points générés."
CODE = "points = [(1, 2), (2, 4), (3, 6)]\nprint(points[2][1] / points[2][0])"
COURSE = (
    "## Notions de base\n\n" + MATERIAL + "\n\n## Limites\n\n"
    "Cet exemple décrit un cas exact, sans bruit de mesure."
)


def attach_article(app: FastAPI) -> None:
    memory = app.state.injected_memory_providers
    assert isinstance(memory.web, FakeWebReader)
    memory.web.pages[URL] = WebDocument(URL, TITLE, MATERIAL, None, None, "fr", None)
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            current.state.providers.sandbox = FakeSandbox({"*": "2.0\n"})
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--origin", default="http://localhost:5200")
    args = parser.parse_args()
    directory = prepare_data_dir(args.data_dir)
    settings = e2e_settings(directory, origin=args.origin, port=args.port)
    migrate(settings)
    result = json.dumps(
        {
            "title": TITLE,
            "course": COURSE,
            "source_quote": QUOTE,
            "experiment": {
                "method": "Calculer la pente des points alignés.",
                "code": CODE,
                "expected": RESULT,
            },
        },
        ensure_ascii=False,
    )
    app = build_app(settings, scripts={"writer": [result]})
    attach_article(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
