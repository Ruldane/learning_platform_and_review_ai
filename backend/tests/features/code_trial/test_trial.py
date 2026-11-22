"""Le verdict et les citations sont liés au projet figé de la séance."""

import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel

from app.agents.runtime.invoke import message_text
from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeLlmProvider
from tests import sessions_support
from tests.sessions_support import wait_status

SOURCE = {
    "main.py": "from rules import total\n\nprint(total([1, 2]))\n",
    "rules.py": "def total(values):\n    return sum(values)\n",
}
SCRIPT = [
    json.dumps(
        {
            "argument": "La coordination dans le point d’entrée se teste difficilement.",
            "references": [1, 99, 1],
        }
    ),
    json.dumps({"argument": "Le calcul reste séparé de la présentation.", "references": [2]}),
]
VERDICT = {
    "choice": "compromise",
    "reason": "Je garde le calcul séparé et j’isole la présentation.",
}


class TrialModels:
    def __init__(self) -> None:
        self.provider = FakeLlmProvider(SCRIPT)
        self.go = asyncio.Event()

    def prompts(self) -> list[str]:
        return [
            "\n".join(message_text(message) for message in row) for row in self.provider.received
        ]

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        await self.go.wait()
        return self.provider.build("modèle fictif", "clé fictive")


@pytest.fixture
def scripted_trial(monkeypatch: pytest.MonkeyPatch, app: FastAPI) -> TrialModels:
    monkeypatch.setattr(sessions_support, "TIMEOUT", 20.0)
    scripted = TrialModels()
    app.state.injected_chat_models = scripted
    return scripted


async def prepare_project(client: httpx.AsyncClient) -> tuple[str, int]:
    created = await client.post("/api/v1/ide/sessions", json={"title": "Projet fictif"})
    assert created.status_code == 201, created.text
    path = f"/api/v1/ide/sessions/{created.json()['id']}"
    save = await client.put(f"{path}/files", json={"files": SOURCE})
    assert save.status_code == 200, save.text
    version: int = save.json()["files_version"]
    return path, version


async def test_trial_freezes_code_and_preserves_a_reasoned_verdict(
    scripted_trial: TrialModels, client: httpx.AsyncClient
) -> None:
    project, version = await prepare_project(client)
    path = f"{project}/code-trials"
    assert (await client.get(path)).json() is None
    opened = await client.post(path)
    assert opened.status_code == 202, opened.text
    started = opened.json()
    trial = f"{path}/{started['trial_id']}"
    assert (await client.post(path)).json() == started
    blocked = await client.put(f"{trial}/verdict", json=VERDICT)
    assert blocked.status_code == 409

    replacement = {**SOURCE, "rules.py": "# version suivante\n"}
    assert (await client.put(f"{project}/files", json={"files": replacement})).status_code == 200
    scripted_trial.go.set()
    try:
        await wait_status(client, started["session_id"], "completed")
    except TimeoutError:
        response = (await client.get(f"/api/v1/sessions/{started['session_id']}")).json()
        pytest.fail(f"Session {response.get('status')}, erreur {response.get('error')}.")
    prompts = scripted_trial.prompts()
    result = (await client.get(trial)).json()
    assert result["files_version"] == version and result["current"] is False
    assert [item["role"] for item in result["pleadings"]] == ["prosecutor", "defender"]
    cited = [item["citations"] for item in result["pleadings"]]
    assert cited[0] == [
        {"path": "main.py", "start_line": 1, "end_line": 3, "text": SOURCE["main.py"].strip()}
    ]
    assert cited[1][0]["text"] == SOURCE["rules.py"].strip()
    assert len(prompts) == 2 and all("return sum(values)" in prompt for prompt in prompts)
    assert "La coordination" in prompts[1]
    assert all("version suivante" not in prompt for prompt in prompts)

    saved = await client.put(f"{trial}/verdict", json=VERDICT)
    assert saved.status_code == 200 and saved.json()["verdict"] == VERDICT
    assert (await client.put(f"{trial}/verdict", json=VERDICT)).json() == saved.json()
    assert (await client.get(path)).json() == saved.json()
    assert (await client.get(project)).json()["files"] == replacement
