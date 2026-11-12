"""Une application ASGI servie par uvicorn sur un port libre de 127.0.0.1, dans la boucle du
test : le contrôle de fin de phase 4 y parle en vrai HTTP et en vrai WebSocket, sans réseau
externe."""

import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import uvicorn
from fastapi import FastAPI

START_TIMEOUT_S = 30.0


@asynccontextmanager
async def serving(app: FastAPI, *, lifespan: Literal["on", "off"] = "on") -> AsyncIterator[str]:
    """L'adresse (`http://127.0.0.1:<port>`) de `app` servie le temps du bloc."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan=lifespan))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        async with asyncio.timeout(START_TIMEOUT_S):
            while not server.started:
                if task.done():
                    task.result()  # l'erreur de démarrage, telle quelle
                await asyncio.sleep(0.02)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task
        sock.close()
