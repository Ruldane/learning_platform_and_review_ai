"""Les cellules restent dans le projet et leur exécution appartient au bac."""

import httpx
import pytest

from tests.features.ide.conftest import UseSandbox
from tests.features.ide.support import API, new_session

pytestmark = pytest.mark.usefixtures("me")
PATH = "notes/atelier.ipynb"


async def test_saves_notebook_cells_then_runs_and_restores_the_result(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    fake = use_sandbox({"*": "3\n"})
    saved = await new_session(client, {"main.py": ""})
    notebook = f"{API}/sessions/{saved['id']}/notebook"
    created = await client.put(
        notebook,
        json={
            "path": PATH,
            "version": saved["files_version"],
            "cells": [
                {"id": "a", "kind": "code", "source": "x = 1"},
                {"id": "b", "kind": "code", "source": "print(x + 2)"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    started = await client.post(
        f"{notebook}/run",
        json={
            "path": PATH,
            "cell_id": "b",
            "include_previous": True,
        },
    )
    assert started.status_code == 202, started.text
    assert fake.jobs[-1].kind == "notebook"
    assert fake.jobs[-1].source == "x = 1\n\nprint(x + 2)"
    result = await client.get(f"{API}/notebook-runs/{started.json()['id']}")
    assert result.status_code == 200 and result.json()["output"] == "3\n"

    reopened = (await client.get(notebook, params={"path": PATH})).json()
    first, second = reopened["cells"]
    assert first["output"] is None and second["output"] == "3\n"
    document = (await client.get(f"{API}/sessions/{saved['id']}")).json()["files"][PATH]
    assert '"nbformat":4' in document


async def test_a_cell_edited_after_launch_does_not_get_an_old_output(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "ancien\n"})
    saved = await new_session(client, {"main.py": ""})
    notebook = f"{API}/sessions/{saved['id']}/notebook"
    first = {"id": "a", "kind": "code", "source": "print('ancien')"}
    made = await client.put(
        notebook,
        json={
            "path": PATH,
            "version": saved["files_version"],
            "cells": [first],
        },
    )
    started = await client.post(f"{notebook}/run", json={"path": PATH, "cell_id": "a"})
    edited = {**first, "source": "print('nouveau')"}
    edited_response = await client.put(
        notebook,
        json={
            "path": PATH,
            "version": made.json()["files_version"],
            "cells": [edited],
        },
    )
    assert edited_response.status_code == 200
    assert (await client.get(f"{API}/notebook-runs/{started.json()['id']}")).status_code == 200
    last = (await client.get(notebook, params={"path": PATH})).json()
    assert last["cells"][0]["source"] == edited["source"]
    assert last["cells"][0]["output"] is None


async def test_reopening_settles_a_cell_that_finished_while_the_view_was_closed(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "gardé\n"})
    saved = await new_session(client, {"main.py": ""})
    notebook = f"{API}/sessions/{saved['id']}/notebook"
    cell = {"id": "a", "kind": "code", "source": "print('gardé')"}
    created = await client.put(
        notebook,
        json={
            "path": PATH,
            "version": saved["files_version"],
            "cells": [cell],
        },
    )
    assert created.status_code == 200
    assert (
        await client.post(notebook + "/run", json={"path": PATH, "cell_id": "a"})
    ).status_code == 202
    reopened = await client.get(notebook, params={"path": PATH})
    assert reopened.json()["cells"][0]["output"] == "gardé\n"
