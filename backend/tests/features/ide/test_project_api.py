"""Les fichiers et les onglets sont enregistrés par les routes de l'IDE."""

import httpx
import pytest

from tests.features.ide.support import API

pytestmark = pytest.mark.usefixtures("me")


async def test_project_routes_persist_tabs_and_follow_file_renames(
    client: httpx.AsyncClient,
) -> None:
    session = (await client.post(f"{API}/sessions", json={})).json()
    root = f"{API}/sessions/{session['id']}"
    added = await client.post(
        f"{root}/files", json={"path": "src/calcul.py", "content": "x = 3\n", "version": 0}
    )
    assert added.status_code == 201, added.text
    assert added.json()["files_version"] == 1
    saved = await client.put(
        f"{root}/tabs",
        json={"open_paths": ["main.py", "src/calcul.py"], "active_path": "src/calcul.py"},
    )
    assert saved.status_code == 200, saved.text

    renamed = await client.patch(
        f"{root}/files",
        json={"path": "src/calcul.py", "destination": "src/outils.py", "version": 1},
    )
    assert renamed.status_code == 200, renamed.text
    view = (await client.get(root)).json()
    assert view["tabs"] == {
        "open_paths": ["main.py", "src/outils.py"],
        "active_path": "src/outils.py",
    }
    assert view["files"] == {"main.py": "", "src/outils.py": "x = 3\n"}

    stale = await client.request(
        "DELETE", f"{root}/files", json={"path": "src/outils.py", "version": 1}
    )
    assert stale.status_code == 409
    removed = await client.request(
        "DELETE", f"{root}/files", json={"path": "src/outils.py", "version": 2}
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["tabs"] == {"open_paths": ["main.py"], "active_path": "main.py"}
