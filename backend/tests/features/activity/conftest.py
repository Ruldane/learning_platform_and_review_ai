import httpx
import pytest
from fastapi import FastAPI

from tests.features.activity.support import Env


@pytest.fixture
def env(client: httpx.AsyncClient, app: FastAPI) -> Env:
    return Env(app, app.state.local_user_id)
