"""Reprise des appels modèle, distincte des réponses de l'utilisatrice."""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from langchain_core.messages import AIMessage
from langgraph.types import Command, Interrupt
from pydantic import BaseModel
from sqlalchemy import update

from app.agents.runtime.control import Factory, stale_interrupt
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.played_model import PLAY_KIND, PlayedModels
from app.agents.runtime.structured import extract_json_object, parse_reply
from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT, PlayClient, PlayContext, as_client, as_provider
from app.db.models.agents import AgentSession, LlmCall


def models_for(row: AgentSession, usual: ChatModelSource) -> ChatModelSource:
    """La source des modèles de la session, et sa source de parcours rétablie dans le contexte
    de son exécution (reprise, redémarrage) : client joué, ou fournisseur forcé lu par la
    fabrique, ou rien (réglages)."""
    if row.played_by is not None:
        if as_client(row.played_by) is None:
            raise AppError("unknown_play_client", "Client MCP inconnu.", 409)
        PLAY_CONTEXT.set(PlayContext(row.user_id, cast(PlayClient, row.played_by)))
        return PlayedModels(row.played_by)
    provider = as_provider(row.model_provider)
    if row.model_provider is not None and provider is None:
        raise AppError("unknown_model_provider", "Fournisseur du parcours inconnu.", 409)
    # Toujours posé : le menu d'une requête plus tardive (réponse, reprise) ne change pas la
    # source d'un parcours déjà lancé.
    PLAY_CONTEXT.set(PlayContext(row.user_id, None, provider=provider))
    return usual


def public_question(pending: dict[str, Any]) -> dict[str, Any]:
    if "brief" not in pending:
        return pending
    pending["expires_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    return {key: value for key, value in pending.items() if key not in ("brief", "expires_at")}


def restore_delivery(items: Sequence[Interrupt], saved: dict[str, Any]) -> Command[Any] | None:
    for item in items:
        if isinstance(item.value, dict) and (
            item.value.get("brief", {}).get("step_id") == saved["step_id"]
        ):
            return Command(resume={item.id: saved})
    return None


def submission_problem(brief: dict[str, Any], response: str) -> str:
    ref = brief.get("schema_ref")
    if not ref:
        return "" if response.strip() else "La réponse est vide."
    # Les schémas qui dépendent de l'état (entretien, candidature) sont recréés par le nœud.
    if "<locals>" in ref[1]:
        return "" if extract_json_object(response) is not None else "Aucun objet JSON trouvé."
    schema = getattr(sys.modules.get(ref[0]), ref[1], None)
    if not isinstance(schema, type) or not issubclass(schema, BaseModel):
        raise AppError(
            "played_schema_unavailable", "Le schéma de cette étape est indisponible.", 409
        )
    _, problem = parse_reply(schema, AIMessage(content=response))
    return problem


async def claim_step(
    db: Factory, row: AgentSession, step_id: str, response: str
) -> tuple[Command[Any], str]:
    pending = row.pending_interrupt or {}
    brief = pending.get("brief") or {}
    if pending.get("kind") != PLAY_KIND or brief.get("step_id") != step_id:
        raise stale_interrupt(row.status)
    delivery = {"step_id": step_id, "response": response, "fingerprint": brief["fingerprint"]}
    problem = submission_problem(brief, response)
    async with db() as session:
        stmt = (
            update(AgentSession)
            .where(
                AgentSession.user_id == row.user_id,
                AgentSession.id == row.id,
                AgentSession.status == "waiting_user",
                AgentSession.pending_interrupt["brief"]["step_id"].as_string() == step_id,
                AgentSession.pending_interrupt["expires_at"].as_string()
                > datetime.now(UTC).isoformat(),
            )
            .values(status="running", pending_interrupt=None, play_delivery=delivery)
            .returning(AgentSession.id)
        )
        claimed = (await session.execute(stmt)).scalar_one_or_none()
        if claimed is None:
            raise stale_interrupt(row.status)
        session.add(
            LlmCall(
                user_id=row.user_id,
                session_id=row.id,
                graph=row.graph,
                agent=brief["agent"],
                provider="mcp",
                model=row.played_by,
            )
        )
        await session.commit()
    return Command(resume={pending["interrupt_id"]: delivery}), problem
