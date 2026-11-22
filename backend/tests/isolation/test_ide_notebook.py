"""Un compte ne peut lire, éditer ou exécuter le notebook d’un autre."""

from fastapi import FastAPI

from app.providers.sandbox.fake import FakeSandbox
from tests.features.ide.support import API
from tests.isolation.conftest import Browser


async def test_notebook_routes_are_isolated(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    google_app.state.providers.sandbox = FakeSandbox({"*": "fictif"})
    a = await google_client_factory("notebook-a@example.test")
    b = await google_client_factory("notebook-b@example.test")
    session = (await a.post(f"{API}/sessions", json={})).json()
    root = f"{API}/sessions/{session['id']}/notebook"
    path = "exemple.ipynb"
    cells = [{"id": "a", "kind": "code", "source": "print(3)"}]
    assert (await a.put(root, json={"path": path, "version": 0, "cells": cells})).status_code == 200
    assert (await b.get(root, params={"path": path})).status_code == 404
    assert (await b.put(root, json={"path": path, "version": 1, "cells": []})).status_code == 404
    draft = {"path": path, "cell_id": "a"}
    assert (await b.post(f"{root}/run", json=draft)).status_code == 404
    started = await a.post(f"{root}/run", json=draft)
    assert started.status_code == 202
    assert (await b.get(f"{API}/notebook-runs/{started.json()['id']}")).status_code == 404
