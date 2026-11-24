"""Écriture d'une session et, pour un lancement lié, de sa réservation métier."""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.repositories import SessionRepository
from app.core.errors import AppError
from app.core.played import ForcedProvider, PlayClient
from app.db.base import new_id
from app.db.models.agents import AgentSession

type PrepareSession = Callable[[AsyncSession, str], Awaitable[None]]


def validated_input(model: type[BaseModel], input: dict[str, Any]) -> dict[str, Any]:
    try:
        return model.model_validate(input).model_dump(mode="json")
    except ValidationError as exc:
        fields = [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
        raise AppError(
            "invalid_input", "The workflow input is invalid.", 422, {"fields": fields}
        ) from None


async def persist_session(
    factory: async_sessionmaker[AsyncSession],
    user_id: str,
    graph: str,
    data: dict[str, Any],
    *,
    source: tuple[PlayClient | None, ForcedProvider | None],
    subject: tuple[str | None, str | None],
    prepare: PrepareSession | None,
) -> str:
    fields = dict(
        graph=graph,
        played_by=source[0],
        model_provider=source[1],
        status="running",
        input=data,
        subject_type=subject[0],
        subject_id=subject[1],
    )
    async with factory() as db:
        if prepare is None:
            sid = (await SessionRepository(db, user_id).add(**fields)).id
        else:
            # La session et les événements qu'elle écrit forment l'historique du moteur.
            # L'annulation MCP de l'appel suit la réservation métier enregistrée par prepare.
            sid = new_id()
            await db.execute(insert(AgentSession).values(id=sid, user_id=user_id, **fields))
            await prepare(db, sid)
        await db.commit()
    return sid
