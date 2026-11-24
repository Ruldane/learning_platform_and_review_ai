"""Exécutions dans le bac à sable (factice) : une à la fois, sortie par décalage d'octets, fin
figée avec sa signature d'erreur, bac arrêté ou oublieux, journaux sans contenu."""

import logging

import httpx
import pytest
from fastapi import FastAPI

from app.features.ide.service import error_signature
from app.providers.sandbox.base import SandboxJob, SandboxProgress, SandboxResult
from app.providers.sandbox.fake import FakeSandbox
from tests.features.ide.conftest import UseSandbox
from tests.features.ide.support import API, TRACE, code, new_session, run_row, start_run

pytestmark = pytest.mark.usefixtures("me")


async def test_run_is_accepted_and_reads_its_output(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "bonjour\n"})
    session = await new_session(client)
    started = await start_run(client, session["id"])
    assert started.status_code == 202
    run = started.json()
    assert (run["session_id"], run["kind"], run["entry"]) == (session["id"], "run", "main.py")
    progress = (await client.get(f"{API}/runs/{run['id']}")).json()
    assert progress["output"] == "bonjour\n" and progress["status"] == "done"
    assert (progress["exit_code"], progress["next_offset"], progress["truncated"]) == (0, 8, False)


async def test_second_run_while_running_is_409(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": ("un", "deux", "trois")})
    session = await new_session(client)
    first = (await start_run(client, session["id"])).json()
    second = await start_run(client, session["id"])
    assert (second.status_code, code(second)) == (409, "run_in_progress")
    assert second.json()["error"]["details"] == {"run_id": first["id"]}
    # une autre séance de la même utilisatrice est refusée de même : une seule par utilisatrice
    other = await new_session(client)
    assert (await start_run(client, other["id"])).status_code == 409
    for _ in range(3):  # la fin est lue : le bac est libre
        done = (await client.get(f"{API}/runs/{first['id']}")).json()
    assert done["status"] == "done"
    assert (await start_run(client, session["id"])).status_code == 202


async def test_a_vanished_run_does_not_block_the_next_one(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": ("un", "deux")})
    session = await new_session(client)
    first = (await start_run(client, session["id"])).json()
    use_sandbox({"*": "ok"})  # le bac ne connaît plus le travail (30 minutes de conservation)
    assert (await start_run(client, session["id"])).status_code == 202
    assert (await run_row(app, first["id"])).status == "error"


async def test_run_output_polled_by_offset(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": ("abc", "déf", "ghi")})
    session = await new_session(client)
    run = (await start_run(client, session["id"])).json()
    url = f"{API}/runs/{run['id']}"
    one = (await client.get(url, params={"after": 0})).json()
    assert (one["output"], one["next_offset"], one["status"]) == ("abc", 3, "running")
    assert one["exit_code"] is None and one["duration_ms"] is None
    two = (await client.get(url, params={"after": one["next_offset"]})).json()
    assert (two["output"], two["next_offset"], two["status"]) == ("déf", 7, "running")
    three = (await client.get(url, params={"after": two["next_offset"]})).json()
    assert (three["output"], three["next_offset"], three["status"]) == ("ghi", 10, "done")
    # une fois finie, la sortie vient de la base, à tout décalage (octets UTF-8)
    assert (await client.get(url, params={"after": 3})).json()["output"] == "défghi"
    assert (await client.get(url, params={"after": 10})).json()["output"] == ""
    assert (await client.get(url, params={"after": 0})).json()["output"] == "abcdéfghi"


async def test_run_finished_stores_output_and_signature(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": TRACE})
    session = await new_session(client)
    run = (await start_run(client, session["id"])).json()
    assert (await client.get(f"{API}/runs/{run['id']}")).status_code == 200
    use_sandbox({})  # le bac oublie tout : la fin est déjà figée
    again = (await client.get(f"{API}/runs/{run['id']}")).json()
    assert (again["output"], again["status"]) == (TRACE, "done")
    row = await run_row(app, run["id"])
    assert (row.output, row.status, row.exit_code) == (TRACE, "done", 0)
    assert row.error_signature == error_signature(TRACE, {"main.py"})
    assert row.error_signature is not None and row.requested_by == "app"
    assert "error_signature" not in again


async def test_run_without_error_has_no_signature(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "tout va bien\n"})
    session = await new_session(client)
    run = (await start_run(client, session["id"])).json()
    await client.get(f"{API}/runs/{run['id']}")
    assert (await run_row(app, run["id"])).error_signature is None


async def test_run_timeout_and_killed_statuses_are_kept(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": SandboxResult("timeout", None, 10_000, False)})
    session = await new_session(client)
    run = (await start_run(client, session["id"])).json()
    progress = (await client.get(f"{API}/runs/{run['id']}")).json()
    assert (progress["status"], progress["exit_code"], progress["duration_ms"]) == (
        "timeout",
        None,
        10_000,
    )


async def test_run_entry_must_be_a_file_of_the_session(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "x"})
    session = await new_session(client)
    response = await client.post(
        f"{API}/sessions/{session['id']}/runs", json={"kind": "run", "entry": "absent.py"}
    )
    assert (response.status_code, code(response)) == (422, "entry_missing")


class _DownSandbox(FakeSandbox):
    """Un bac arrêté : le dépôt comme la lecture lèvent `OSError`."""

    async def submit(self, job: SandboxJob) -> None:
        raise OSError("bac arrêté")

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        raise OSError("bac arrêté")


async def test_sandbox_down_gives_readable_error(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    session = await new_session(client)
    app.state.providers.sandbox = _DownSandbox()
    response = await start_run(client, session["id"])
    assert (response.status_code, code(response)) == (503, "sandbox_unavailable")
    assert "The sandbox is not available" in response.json()["error"]["message"]
    # rien n'est resté « en cours » : le bac revenu, l'exécution part
    use_sandbox({"*": "ok"})
    run = await start_run(client, session["id"])
    assert run.status_code == 202
    app.state.providers.sandbox = _DownSandbox()
    read = await client.get(f"{API}/runs/{run.json()['id']}")
    assert (read.status_code, code(read)) == (503, "sandbox_unavailable")
    app.state.providers.sandbox = None  # pas encore composé
    assert code(await start_run(client, session["id"])) == "sandbox_unavailable"


async def test_job_refused_by_the_sandbox_is_422(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    class Refusing(FakeSandbox):
        async def submit(self, job: SandboxJob) -> None:
            raise ValueError("trop gros")

    session = await new_session(client)
    app.state.providers.sandbox = Refusing()
    response = await start_run(client, session["id"])
    assert (response.status_code, code(response)) == (422, "run_refused")


async def test_ide_output_never_logged(
    client: httpx.AsyncClient, use_sandbox: UseSandbox, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "SORTIE-SECRETE-9f3a"
    use_sandbox({"*": f"{secret}\n{TRACE}"})
    caplog.set_level(logging.DEBUG)
    session = await new_session(client, {"main.py": f"print('{secret}')  # code-secret-4b7\n"})
    run = (await start_run(client, session["id"])).json()
    await client.get(f"{API}/runs/{run['id']}")
    await client.get(f"{API}/runs/{run['id']}", params={"after": 5})
    # Nos journaux (`app.*`) : aiosqlite, en DEBUG, journalise les paramètres SQL, c'est un réglage
    # de bibliothèque, jamais actif hors d'une enquête.
    ours = [r for r in caplog.records if r.name.startswith("app.")]
    text = "\n".join(f"{r.name} {r.getMessage()} {r.exc_text or ''}" for r in ours)
    assert "SORTIE-SECRETE" not in text and "code-secret" not in text
    assert "ZeroDivisionError" not in text
    assert run["id"] in text  # on journalise l'identifiant et le statut, rien d'autre


async def test_nul_in_the_output_is_replaced_before_storage(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": ("a\x00b", "c\x00")})
    session = await new_session(client)
    run = (await start_run(client, session["id"])).json()
    url = f"{API}/runs/{run['id']}"
    live = (await client.get(url)).json()
    assert (live["output"], live["next_offset"]) == ("a?b", 3)
    end = (await client.get(url, params={"after": 3})).json()
    assert (end["output"], end["status"], end["next_offset"]) == ("c?", "done", 5)
    assert (await run_row(app, run["id"])).output == "a?bc?"
