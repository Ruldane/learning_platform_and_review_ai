"""Fixtures des tests de l'IDE (10.A2) : l'application réelle, une utilisatrice (`act_as`) et un bac
à sable factice (`FakeSandbox`, jamais le vrai) que le test pose sur `app.state.providers`."""

from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI

from app.providers.sandbox.fake import FakeSandbox, Script
from tests.sessions_support import act_as

USER = "utilisatrice-a"
OTHER = "utilisatrice-b"

UseSandbox = Callable[[dict[str, Script]], FakeSandbox]


@pytest.fixture
def me(app: FastAPI, client: httpx.AsyncClient) -> str:
    """Les requêtes sont celles de `USER`."""
    act_as(app, USER)
    return USER


@pytest.fixture
def use_sandbox(app: FastAPI, client: httpx.AsyncClient) -> UseSandbox:
    """`use_sandbox({"*": "sortie"})` : pose un bac factice scripté (clé `"*"` : tout travail)."""

    def use(scripted: dict[str, Script]) -> FakeSandbox:
        fake = FakeSandbox(scripted)
        app.state.providers.sandbox = fake
        return fake

    return use
