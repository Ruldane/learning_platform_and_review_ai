from fastapi import FastAPI

from tests.features.postings.conftest import add_posting
from tests.support.gap import analysis_data


async def seed_offers(app: FastAPI, user_id: str) -> tuple[str, str]:
    async def add(title: str, location: str, remote: str) -> str:
        return await add_posting(
            app.state.session_factory,
            user_id,
            title=title,
            company="Laboratoire fictif",
            status="ready",
            analysis=analysis_data(title=title, location=location, remote=remote),
        )

    return await add("Mesures A", "Paris", "hybride"), await add("Mesures B", "Lyon", "présentiel")
