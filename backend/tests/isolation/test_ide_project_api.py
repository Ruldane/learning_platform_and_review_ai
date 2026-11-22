"""Un autre compte ne peut modifier ni les fichiers ni les onglets d'un projet."""

from tests.features.ide.support import API
from tests.isolation.conftest import Browser


async def test_foreign_project_file_and_tab_operations_are_refused(
    google_client_factory: Browser,
) -> None:
    owner = await google_client_factory("projet-prive@example.test")
    other = await google_client_factory("projet-tiers@example.test")
    session = (await owner.post(f"{API}/sessions", json={})).json()
    root = f"{API}/sessions/{session['id']}"

    for method, path, data in (
        ("POST", "files", {"path": "secret.py", "version": 0}),
        ("PATCH", "files", {"path": "main.py", "destination": "secret.py", "version": 0}),
        ("DELETE", "files", {"path": "main.py", "version": 0}),
        ("PUT", "tabs", {"open_paths": ["main.py"], "active_path": "main.py"}),
    ):
        response = await other.request(method, f"{root}/{path}", json=data)
        assert response.status_code == 404, response.text
    assert (await owner.get(root)).json()["files"] == {"main.py": ""}
