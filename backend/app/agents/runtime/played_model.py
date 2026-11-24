"""Le modèle joué transforme la demande exacte du nœud en interruption du graphe."""

import hashlib
import json
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.types import interrupt

from app.core.errors import AppError
from app.providers.llm.base import Tier

PLAY_KIND = "mcp_model"


class PlayedChat(BaseChatModel):
    role: str
    schema_ref: tuple[str, str] | None = None
    expected_schema: dict[str, Any] | None = None
    refresh_changed_brief: bool = False

    @property
    def _llm_type(self) -> str:
        return "mcp"

    def _generate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> ChatResult:
        rows = [{"role": m.type, "content": m.content} for m in messages]
        brief = {"agent": self.role, "messages": rows, "output_schema": self.expected_schema}
        raw = json.dumps(brief, sort_keys=True, ensure_ascii=False).encode()
        key = hashlib.sha256(raw).hexdigest()
        while True:
            value = interrupt(
                {
                    "kind": PLAY_KIND,
                    "question": "Waiting for the MCP client to respond.",
                    "brief": {
                        **brief,
                        "step_id": str(uuid4()),
                        "fingerprint": key,
                        "schema_ref": self.schema_ref,
                    },
                }
            )
            if not isinstance(value, dict) or not all(
                isinstance(value.get(field), str)
                for field in ("fingerprint", "step_id", "response")
            ):
                break
            if value["fingerprint"] == key:
                message = AIMessage(content=value["response"], id=value["step_id"])
                return ChatResult(generations=[ChatGeneration(message=message)])
            if not self.refresh_changed_brief:
                break
            # LangGraph rejoue les anciennes livraisons avant de suspendre au nouveau brief.
        raise AppError("played_step_changed", "The request for this step has changed.", 409)

    async def _agenerate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        return self._generate(messages)


def refresh_updated_brief(model: BaseChatModel) -> BaseChatModel:
    """Republie le brief d'un appel dont les consignes sont susceptibles d'avoir changé."""
    if isinstance(model, PlayedChat):
        return model.model_copy(update={"refresh_changed_brief": True})
    return model


class PlayedModels:
    def __init__(self, client: str) -> None:
        self.client = client

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        return PlayedChat(
            role=agent or "",
            metadata={
                "tremplin_provider": "mcp",
                "tremplin_model": self.client,
            },
        )
