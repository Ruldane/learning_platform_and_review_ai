"""Recette du graphe, des voix et de la correction du podcast en boucle locale."""

import argparse
import json
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from langchain_core.messages import BaseMessage

from app.db.base import new_id
from app.db.models.lessons import Lesson
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from app.providers.speech.base import PCM_RATE, Speaker
from tests.e2e.lesson_script import prompt_of
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.program.support import MONDAY, add_goal, sample_plan

TITLE = "Composer des chaînes de traitement"
LESSON = "Une chaîne de traitement fait circuler une valeur entre ses étapes."
TURN = "Une chaîne conserve le résultat utile avant de transmettre la valeur suivante. "
SCRIPT = [
    ("host", "Aujourd’hui, nous suivons une valeur."),
    ("coach", "Une chaîne relie plusieurs étapes."),
] * 4
QUESTIONS = [
    (
        "Par quoi commence la chaîne ?",
        ["Une entrée", "Une archive", "Un tableau vide"],
        0,
        "Le premier maillon reçoit l’entrée.",
    ),
    (
        "Que transmet le premier maillon ?",
        ["Sa durée", "Son résultat", "Son nom"],
        1,
        "Le résultat devient l’entrée du maillon suivant.",
    ),
    (
        "Comment contrôler le résultat ?",
        ["Changer le sujet", "Ignorer l’entrée", "Comparer avec la sortie attendue"],
        2,
        "La sortie attendue sert de repère.",
    ),
]


class LocalVoices:
    async def speak(self, user_id: str, speaker: Speaker, text: str) -> bytes:
        # La durée de recette atteint la plage publique avec du PCM local.
        seconds = 75 if speaker == "host" else 77
        return b"\0\0" * (PCM_RATE * seconds)


def scripted_episode(messages: Sequence[BaseMessage]) -> str:
    if LESSON not in prompt_of(messages):
        raise AssertionError("Le chapitre de recette manque dans le contexte du podcast.")
    return json.dumps(
        {
            "lines": [
                {"speaker": role, "text": prefix + " " + TURN * 17} for role, prefix in SCRIPT
            ],
            "questions": [
                {
                    "question": question,
                    "choices": choices,
                    "answer": answer,
                    "explanation": explanation,
                }
                for question, choices, answer, explanation in QUESTIONS
            ],
        },
        ensure_ascii=False,
    )


async def seed_chapter(app: FastAPI) -> None:
    owner = app.state.local_user_id
    factory = app.state.session_factory
    goal = await add_goal(factory, owner)
    draft = await AgentProgramStore(app.state.program).save_draft(
        owner,
        new_id(),
        goal.goal_id,
        sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Programme audio de recette",
    )
    async with factory() as db:
        loaded = await load(db, owner, draft.program_id)
        loaded.program.status = "validated"
        db.add(
            Lesson(
                user_id=owner,
                program_id=draft.program_id,
                module_id=loaded.modules[0].id,
                title=TITLE,
                markdown=f"## Explication\n\n{LESSON}\n",
                status="ready",
            )
        )
        await db.commit()


def configure(app: FastAPI) -> None:
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            podcast: PodcastRuntime = current.state.daily.podcast
            podcast.now = lambda: datetime(MONDAY.year, MONDAY.month, MONDAY.day, 9, tzinfo=UTC)
            podcast.speech = LocalVoices()
            await seed_chapter(current)
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8893)
    parser.add_argument("--origin", default="http://127.0.0.1:5293")
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"podcast_host": [scripted_episode]})
    configure(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
