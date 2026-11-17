"""Les exercices générés (10.A3) : l'exercice n'est rangé qu'une fois sa solution passée dans le bac
à sable (factice ici) ; une solution qui échoue est redemandée une fois, puis le parcours échoue
lisiblement. La solution n'est jamais rangée."""

import json
from typing import Any

import httpx
import pytest

from app.providers.sandbox.base import SandboxJob, SandboxResult
from app.providers.sandbox.fake import FakeSandbox
from tests.features.ide.conftest import UseSandbox
from tests.features.ide.support import API
from tests.features.ide.teach_support import ScriptedModels, wait_done
from tests.sessions_support import wait_status

pytestmark = pytest.mark.usefixtures("me")

TESTS = "from main import double\n\ndef test_double():\n    assert double(2) == 4\n"
SOLUTION = "def double(n):\n    return n * 2\n"


def draft(**over: Any) -> str:
    data: dict[str, Any] = {
        "title": "Doubler un nombre",
        "statement": "Écris `double(n)` qui renvoie le double de `n`. Exemple : double(2) == 4.",
        "entry": "main.py",
        "files": {"main.py": "def double(n):\n    # TODO\n    pass\n", "test_main.py": TESTS},
        "solution": {"main.py": SOLUTION, "test_main.py": "def test_double():\n    assert True\n"},
    }
    return json.dumps(data | over)


class RecordingSandbox(FakeSandbox):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.jobs: list[SandboxJob] = []

    async def submit(self, job: SandboxJob) -> None:
        self.jobs.append(job)
        await super().submit(job)


@pytest.fixture
def sandbox(app: Any) -> RecordingSandbox:
    box = RecordingSandbox({"*": "1 passed in 0.01s"})
    app.state.providers.sandbox = box
    return box


async def generate(client: httpx.AsyncClient) -> str:
    sent = await client.post(f"{API}/exercises/generate", json={"topic": "les fonctions"})
    assert sent.status_code == 202
    session_id: str = sent.json()["session_id"]
    return session_id


async def test_generated_exercise_solution_passes_checks_in_sandbox(
    client: httpx.AsyncClient, models: ScriptedModels, sandbox: RecordingSandbox
) -> None:
    models.replies.append(draft())
    sid = await generate(client)
    done = await wait_done(client, sid)
    assert done["status"] == "completed"
    [job] = sandbox.jobs
    assert job.kind == "check" and job.entry == "main.py"
    assert job.files["main.py"] == SOLUTION  # la solution est celle qui tourne
    assert job.files["test_main.py"] == TESTS  # mais les tests sont ceux de l'exercice
    [exercise] = (await client.get(f"{API}/exercises")).json()
    assert exercise["origin"] == "generated" and exercise["topic"] == "les fonctions"
    assert exercise["files"]["main.py"].count("TODO") == 1 and exercise["files"]["test_main.py"]
    assert SOLUTION not in json.dumps(exercise)  # la solution n'est jamais rangée
    assert (models.calls[0].tier, models.calls[0].agent) == ("standard", "exercise_writer")
    opened = await client.post(f"{API}/sessions", json={"exercise_id": exercise["id"]})
    assert opened.status_code == 201 and opened.json()["files"]["main.py"].endswith("pass\n")


async def test_generated_exercise_with_failing_solution_regenerates_once_then_fails_readably(
    app: Any, client: httpx.AsyncClient, models: ScriptedModels, use_sandbox: UseSandbox
) -> None:
    failing = SandboxResult(status="done", exit_code=1, duration_ms=5, truncated=False)
    fake = use_sandbox({"*": failing})
    models.replies += [draft(), draft(title="Doubler, deuxième essai")]
    sid = await generate(client)
    view = await wait_status(client, sid, "failed")
    assert view["error"]["code"] == "exercise_unverified"
    assert "relance" in view["error"]["message"]
    assert len(models.calls) == 2  # une seule redemande, jamais plus
    assert (await client.get(f"{API}/exercises")).json() == []  # rien de non vérifié n'est rangé
    assert fake is app.state.providers.sandbox


async def test_failing_solution_then_good_one_is_stored(
    client: httpx.AsyncClient, models: ScriptedModels, sandbox: RecordingSandbox
) -> None:
    results = iter([SandboxResult("done", 1, 5, False), "1 passed"])

    async def submit(job: SandboxJob) -> None:
        sandbox.jobs.append(job)
        sandbox._scripted = {"*": next(results)}  # type: ignore[assignment]
        await FakeSandbox.submit(sandbox, job)

    sandbox.submit = submit  # type: ignore[method-assign]
    models.replies += [draft(), draft(title="Doubler, corrigé")]
    sid = await generate(client)
    await wait_done(client, sid)
    [exercise] = (await client.get(f"{API}/exercises")).json()
    assert exercise["title"] == "Doubler, corrigé" and len(sandbox.jobs) == 2
    retry = str(models.received[1][-2].content) + str(models.received[1][0].content)
    assert "sortie des tests" in retry  # la redemande dit pourquoi


async def test_draft_without_tests_is_refused_after_the_retries(
    client: httpx.AsyncClient, models: ScriptedModels, sandbox: RecordingSandbox
) -> None:
    no_tests = draft(files={"main.py": "x = 1\n"})
    models.replies += [no_tests, no_tests, no_tests]
    sid = await generate(client)
    view = await wait_status(client, sid, "failed")
    assert view["error"]["code"] == "structured_output_invalid" and sandbox.jobs == []
