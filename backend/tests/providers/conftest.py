from collections.abc import AsyncIterator

import httpx
import pytest


@pytest.fixture
async def http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=3.0) as client:
        yield client
