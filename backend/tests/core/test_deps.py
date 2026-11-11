from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient

from app.core.deps import CurrentUserDep, get_cipher, get_llm_factory, get_providers
from app.core.providers import Providers
from app.core.security import Cipher
from app.providers.llm.factory import LlmFactory


def test_core_dependencies_work_on_websocket_routes(app: FastAPI) -> None:
    # Le flux temps réel (phase 1) passe par WebSocket : les dépendances du socle doivent y
    # être injectables (FastAPI n'injecte pas `Request` sur une route WebSocket).
    @app.websocket("/api/v1/_ws")
    async def ws(
        websocket: WebSocket,
        user: CurrentUserDep,
        providers: Annotated[Providers, Depends(get_providers)],
        factory: Annotated[LlmFactory, Depends(get_llm_factory)],
        cipher: Annotated[Cipher, Depends(get_cipher)],
    ) -> None:
        await websocket.accept()
        await websocket.send_json(
            {
                "user": user.id,
                "factory": factory is providers.llm_factory,
                "cipher": isinstance(cipher, Cipher),
            }
        )
        await websocket.close()

    with TestClient(app) as client, client.websocket_connect("/api/v1/_ws") as ws_conn:
        data = ws_conn.receive_json()

    assert data["user"] == app.state.local_user_id
    assert data == {"user": data["user"], "factory": True, "cipher": True}
