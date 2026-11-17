"""Le client HTTP du point `token` de Google : ouvert en mode Google seulement, toujours fermé."""

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.config import Settings
from app.main import create_app


async def test_google_mode_closes_the_token_client(
    google_settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    def boom(*args: object, **kwargs: object) -> None:
        raise ValueError("composition cassée")

    monkeypatch.setattr("app.main.httpx.AsyncClient", tracking)
    monkeypatch.setattr("app.main.build_providers", boom)
    with pytest.raises(ValueError, match="composition cassée"):
        async with LifespanManager(create_app(google_settings)):
            pass
    # Sondes, clé Brave et, en mode Google seulement, le point `token` : tous fermés.
    assert len(created) == 3 and all(c.is_closed for c in created)
