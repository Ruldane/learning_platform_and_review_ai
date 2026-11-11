"""Sortie structurée : du JSON conforme à un modèle Pydantic, validé, avec nouveaux essais.

On n'utilise pas `with_structured_output` (D44) : le faux fournisseur des tests et les trois
fournisseurs réels passent ainsi par le même chemin, et une réponse vide ou mal formée (GLM)
se retente de la même façon partout.
"""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import call_with_retries, message_text
from app.core.errors import AppError

_INSTRUCTIONS = (
    "Réponds uniquement par un objet JSON conforme à ce schéma JSON, sans texte autour ni "
    "balises de code :\n{schema}"
)
_EMPTY = "La réponse était vide."
_RETRY = (
    "Ta réponse précédente n'est pas valide : {problem}\n"
    "Réponds de nouveau, uniquement par un objet JSON conforme au schéma."
)


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Premier objet JSON de `text` (au milieu de texte ou d'une balise de code), sinon `None`."""
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
    """Champs fautifs et motifs de pydantic, sans les valeurs reçues."""
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or '(racine)'} : {e['msg']}" for e in exc.errors()
    )


def _parse[T: BaseModel](schema: type[T], reply: AIMessage) -> tuple[T | None, str]:
    """`(résultat, "")` ou `(None, problème à renvoyer au modèle)`."""
    text = message_text(reply)
    if not text.strip():
        return None, _EMPTY
    data = extract_json_object(text)
    if data is None:
        return None, "aucun objet JSON trouvé dans la réponse."
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
    """Demande du JSON conforme à `schema`. En cas d'échec, renvoie le problème au modèle et
    retente ; après `1 + retries` essais : `AppError("structured_output_invalid")`."""
    emit("agent.started", {"step": step, "intent": intent}, agent=agent)
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    conversation = [*messages, HumanMessage(_INSTRUCTIONS.format(schema=schema_json))]
    attempts = 1 + retries
    for attempt in range(attempts):
        reply = await call_with_retries(  # JSON brut : pas de tokens en direct
            model, conversation, agent=agent, allow_empty=True, stream=False
        )
        result, problem = _parse(schema, reply)
        if result is not None:
            return result
        if attempt < attempts - 1:
            text = message_text(reply)
            if text.strip():  # une réponse vide est refusée par certaines API si on la renvoie
                conversation.append(AIMessage(text))
            conversation.append(HumanMessage(_RETRY.format(problem=problem)))
    raise AppError(
        "structured_output_invalid",
        f"La réponse de l'agent {agent} n'a pas le format attendu après {attempts} essais.",
        502,
        {"agent": agent, "attempts": attempts},
    )
