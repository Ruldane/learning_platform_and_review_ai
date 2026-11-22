"""Client de complétions OpenAI de l'IDE sur le canal privé de cette exécution."""

import json
import os
import socket
import threading
from typing import Any

_LOCK = threading.Lock()
_REQUEST_BYTES, _REPLY_BYTES = 16_384, 100_000


def create_chat_completion(
    *, model: str, messages: list[dict[str, str]], max_tokens: int = 256
) -> dict[str, Any]:
    """Envoie une demande texte bornée et rend le champ `choices` d'une complétion de chat."""
    payload = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens})
    frame = payload.encode() + b"\n"
    if len(frame) > _REQUEST_BYTES:
        raise ValueError("gateway_request_invalid")
    try:
        fd = int(os.environ["TREMPLIN_MODEL_FD"])
        with _LOCK, socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.sendall(frame)
            with channel.makefile("rb") as stream:
                raw = stream.readline(_REPLY_BYTES + 1)
        if len(raw) > _REPLY_BYTES or not raw.endswith(b"\n"):
            raise OSError("préfixe de réponse invalide")
        response = json.loads(raw)
    except (OSError, ValueError, KeyError):
        raise RuntimeError("gateway_unavailable") from None
    if "error" in response:
        raise RuntimeError(response["error"])
    message = {"role": "assistant", "content": response["content"]}
    return {"model": model, "choices": [{"index": 0, "message": message, "finish_reason": "stop"}]}
