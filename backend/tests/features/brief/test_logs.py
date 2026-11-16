"""Journaux du brief (17.2) : identifiants, nombres et codes seulement. Jamais une rubrique, une
entreprise, un intitulé, un lien, une ressource, une phrase du conseil ni le poste visé."""

import logging

import httpx
import pytest

from app.agents.tools.brief_schema import ResourceView
from app.features.brief.service.schedule import run_daily_briefs
from app.features.brief.service.store import AgentBriefStore
from app.features.settings.service import SettingsService
from tests.features.brief.conftest import Env
from tests.features.brief.support import add_cards, add_run, applied, get_today, posting
from tests.features.study.conftest import seed

SECRETS = (
    "Société Fictive",
    "Développeuse IA",
    "Poste 1",
    "example.org",
    "Leçon Module Bases",
    "Lire le chapitre",
    "Ingénieur IA",
    "Guide secret",
    "Phrase secrète du conseil",
    "Raison secrète",
)
VIEW = ResourceView(
    "Guide secret", "https://docs.example.org/guide", "docs.example.org", None, "Raison secrète."
)


def _text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


async def test_brief_data_never_logged(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient, env: Env
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await seed(env.app)
    env.at(env.rt.now())
    await add_cards(env, 3)
    await applied(client, 8)
    await add_run(env, [posting(1, 90)])
    async with env.rt.session_factory() as db:
        service = SettingsService(db, env.user_id)
        await service.replace(
            (await service.get()).model_copy(update={"radar_role": "Ingénieur IA"})
        )
        await db.commit()
    body = await get_today(client)  # création, lancement
    store = AgentBriefStore(env.rt)
    await store.context(env.user_id, body["id"])
    await store.save_resource(env.user_id, body["session_id"], body["id"], VIEW)
    await store.save_advice(
        env.user_id, body["session_id"], body["id"], ["Phrase secrète du conseil.", "Autre."]
    )
    await env.launcher.end(env.user_id, body["session_id"], "failed")
    await get_today(client)
    await run_daily_briefs(env.rt, env.rt.now())
    text = _text(caplog)
    for secret in SECRETS:
        assert secret not in text, secret
    assert body["id"] in text and "Brief" in text  # des identifiants et des nombres, oui


async def test_launch_failure_logs_only_a_code(
    caplog: pytest.LogCaptureFixture, client: httpx.AsyncClient, env: Env
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")

    async def broken(*args: object, **kwargs: object) -> str:
        raise RuntimeError("Donnée secrète : Société Fictive")

    env.launcher.start = broken  # type: ignore[method-assign]
    await get_today(client)
    text = _text(caplog)
    assert "RuntimeError" in text and "Donnée secrète" not in text and "Société" not in text
