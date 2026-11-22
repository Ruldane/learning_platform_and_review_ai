"""Canal de la passerelle partagé exclusivement avec le lanceur du bac."""

import asyncio
import json
import os
import stat
from contextlib import suppress
from pathlib import Path

from app.core.errors import AppError
from app.features.ide.service.model_gateway import MAX_REQUEST_BYTES, ModelGateway

SOCKET_NAME = "ide-model.sock"
_FRAME_BYTES = MAX_REQUEST_BYTES + 512


async def _complete(gateway: ModelGateway, payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("enveloppe invalide")
    owner, run = payload.get("user_id"), payload.get("run_id")
    if not isinstance(owner, str) or not isinstance(run, str) or len(owner) > 36 or len(run) > 36:
        raise ValueError("travail invalide")
    if not await gateway.allowed_run(owner, run):
        raise AppError("gateway_run_refused", "Ce travail ne dispose pas de la passerelle.", 403)
    return await gateway.complete(owner, payload.get("request"))


async def _serve(
    gateway: ModelGateway, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        async with asyncio.timeout(10):
            raw = await reader.readline()
            if not raw.endswith(b"\n") or len(raw) > _FRAME_BYTES:
                raise ValueError("requête modèle illisible")
            content = await _complete(gateway, json.loads(raw))
            result: dict[str, str] = {"content": content}
    except AppError as exc:
        result = {"error": exc.code}
    except (ValueError, OverflowError, RecursionError):
        result = {"error": "gateway_request_invalid"}
    except Exception:
        result = {"error": "gateway_unavailable"}
    try:
        writer.write(json.dumps(result).encode() + b"\n")
        await writer.drain()
    except OSError:
        pass
    finally:
        writer.close()
        with suppress(OSError):
            await writer.wait_closed()


async def _remove_stale(path: Path) -> bool:
    try:
        old = path.lstat()
    except FileNotFoundError:
        return True
    if not stat.S_ISSOCK(old.st_mode) or old.st_uid != os.getuid():
        return False
    try:
        _, writer = await asyncio.open_unix_connection(path)
    except ConnectionRefusedError:
        if path.lstat().st_ino != old.st_ino:
            return False
        path.unlink()
        return True
    writer.close()
    await writer.wait_closed()
    return False


class ModelSocket:
    def __init__(self, path: Path, server: asyncio.Server) -> None:
        self._path = path
        self._inode = path.lstat().st_ino
        self._server = server

    async def close(self) -> None:
        self._server.close()
        await self._server.wait_closed()
        with suppress(FileNotFoundError):
            if self._path.lstat().st_ino == self._inode:
                self._path.unlink()


async def open_model_socket(directory: Path, gateway: ModelGateway) -> ModelSocket | None:
    if os.name != "posix" or not directory.is_dir():
        return None
    path = directory / SOCKET_NAME
    if not await _remove_stale(path):
        return None
    server = await asyncio.start_unix_server(
        lambda reader, writer: _serve(gateway, reader, writer), path=path, limit=_FRAME_BYTES
    )
    try:
        path.chmod(0o660)
        return ModelSocket(path, server)
    except OSError:
        server.close()
        await server.wait_closed()
        path.unlink(missing_ok=True)
        return None
