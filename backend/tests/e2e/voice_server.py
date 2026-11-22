"""Recette vocale locale sur un micro et des fournisseurs synthétiques."""

import argparse
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from langchain_core.messages import BaseMessage

from tests.agents.graphs.interview_support import debrief_json, plan_json, turn_json
from tests.e2e.scripted_models import OutOfOrder
from tests.e2e.server import build_app, e2e_settings, migrate, prepare_data_dir
from tests.features.applications.interview_support import add_profile
from tests.support.voice import VoiceDouble

CORRECTED = "Je structure ma réponse avec le contexte, l’action et le résultat."


def assess(messages: Sequence[BaseMessage]) -> str:
    if not any(CORRECTED in str(message.content) for message in messages):
        raise OutOfOrder("L’entretien attend la réponse relue par l’utilisatrice.")
    return turn_json(note=4)


def use_voice_doubles(app: FastAPI) -> None:
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with original(current):
            await add_profile(current)
            voice = VoiceDouble()
            current.state.voice.transcription = current.state.voice.speech = voice
            yield

    app.router.lifespan_context = lifespan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    settings = e2e_settings(prepare_data_dir(args.data_dir), origin=args.origin, port=args.port)
    migrate(settings)
    app = build_app(settings, scripts={"interviewer": [plan_json(), assess, debrief_json()]})
    use_voice_doubles(app)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
