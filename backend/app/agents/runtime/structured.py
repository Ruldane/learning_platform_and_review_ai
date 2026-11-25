"""Structured output: JSON matching a Pydantic model, validated, with retries.

`with_structured_output` is not used (D44): the tests' fake provider and the three real
providers thus go through the same path, and an empty or malformed reply (GLM) is retried
the same way everywhere.
"""

import json
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import call_with_retries, message_text
from app.agents.runtime.played_model import PlayedChat
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_INSTRUCTIONS = (
    "Reply with a JSON object that matches this schema. Omit surrounding text and code fences.\n"
    "{schema}"
)
_EMPTY = "The reply was empty."
_RETRY = (
    "Your previous reply is invalid: {problem}\n"
    "Send a new reply containing only a JSON object that matches the schema."
)


def extract_json_object(text: str) -> dict[str, Any] | None:
    """First JSON object of `text` (in the middle of text or a code fence), otherwise `None`."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(text, start)
        except ValueError:
            start = text.find("{", start + 1)
            continue
        return value if isinstance(value, dict) else None
    return None


def _validation_problem(exc: ValidationError) -> str:
    """Faulty fields and reasons from pydantic, without the received values."""
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or '(root)'}: {e['msg']}" for e in exc.errors()
    )


def parse_reply[T: BaseModel](schema: type[T], reply: AIMessage) -> tuple[T | None, str]:
    """`(result, "")` or `(None, problem to send back to the model)`."""
    text = message_text(reply)
    if not text.strip():
        return None, _EMPTY
    data = extract_json_object(text)
    if data is None:
        return None, "No JSON object found in the reply."
    try:
        return schema.model_validate(data), ""
    except ValidationError as exc:
        return None, _validation_problem(exc)


async def structured_call[T: BaseModel](
    model: BaseChatModel,
    schema: type[T],
    messages: list[BaseMessage],
    *,
    agent: str,
    step: str,
    intent: str,
    retries: int = 2,
) -> T:
    """Asks for JSON matching `schema`. On failure, sends the problem back to the model and
    retries; after `1 + retries` attempts: `AppError("structured_output_invalid")`."""
    emit("agent.started", {"step": step, "intent": intent}, agent=agent)
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    if isinstance(model, PlayedChat):
        model = model.model_copy(
            update={
                "expected_schema": schema.model_json_schema(),
                "schema_ref": (schema.__module__, schema.__qualname__),
            }
        )
    conversation = [*messages, HumanMessage(_INSTRUCTIONS.format(schema=schema_json))]
    attempts = 1 + retries
    for attempt in range(attempts):
        reply = await call_with_retries(  # raw JSON: no live tokens
            model, conversation, agent=agent, allow_empty=True, stream=False
        )
        result, problem = parse_reply(schema, reply)
        if result is not None:
            return result
        # Pydantic's field and reason only: neither the received value nor content (SPEC 17.2).
        logger.warning(
            "Structured output refused: agent %s, step %s, attempt %d/%d, %s",
            agent,
            step,
            attempt + 1,
            attempts,
            problem,
        )
        if attempt < attempts - 1:
            text = message_text(reply)
            if text.strip():  # some APIs refuse an empty reply if it is sent back
                conversation.append(AIMessage(text))
            conversation.append(HumanMessage(_RETRY.format(problem=problem)))
    raise AppError(
        "structured_output_invalid",
        f"The {agent} agent's reply had the wrong format after {attempts} attempts.",
        502,
        {"agent": agent, "attempts": attempts},
    )
