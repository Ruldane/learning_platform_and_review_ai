"""Outils des tests de « Tout supprimer » : tout ce qu'un compte laisse derrière lui (lignes,
fichiers, vecteurs, points de reprise) et de quoi le compter, pour deux comptes."""

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI
from langgraph.checkpoint.base import BaseCheckpointSaver, empty_checkpoint
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.agents.runtime.checkpointer import thread_config
from app.db.base import Base
from app.db.models.agents import AgentSession
from app.db.models.learning import Goal
from app.providers.vector.base import ChunkToIndex
from tests.support.account import OTHER, seed_other_user, seed_user
from tests.support.memory import make_chunk

CAMILLE = "camille-0000-0000-0000-000000000001"
DELETE = "/api/v1/account/delete"
BODY = {"confirm": "SUPPRIMER"}


def saver_of(app: FastAPI) -> BaseCheckpointSaver[Any]:
    """Le checkpointer du moteur d'agents de l'application de test."""
    saver: BaseCheckpointSaver[Any] = app.state.runtime.runner._ctx.checkpointer
    return saver


async def put_checkpoint(saver: BaseCheckpointSaver[Any], thread_id: str) -> None:
    config = thread_config(thread_id)
    config["configurable"]["checkpoint_ns"] = ""  # le saver le demande à l'écriture
    metadata: Any = {"source": "input", "step": 0, "parents": {}}
    await saver.aput(config, empty_checkpoint(), metadata, {})


async def has_checkpoint(saver: BaseCheckpointSaver[Any], thread_id: str) -> bool:
    return await saver.aget_tuple(thread_config(thread_id)) is not None


async def row_counts(db: AsyncSession, user_id: str) -> dict[str, int]:
    """Le nombre de lignes de `user_id` dans **chaque** table de la base qui a `user_id`."""
    counts: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        if "user_id" in table.c:
            stmt = select(func.count()).select_from(table).where(table.c.user_id == user_id)
            counts[table.name] = (await db.execute(stmt)).scalar_one()
    return counts


@dataclass
class Footprint:
    """Ce qu'un compte a posé : ses fichiers, ses fils de points de reprise, ses vecteurs."""

    user_id: str
    files: list[str]
    threads: list[str]
    chunk: ChunkToIndex


async def seed_footprint(
    db: AsyncSession,
    app: FastAPI,
    user_id: str,
    tag: str,
    *,
    statuses: tuple[str, ...] = ("completed",),
) -> Footprint:
    """Des lignes de plusieurs tables (`seed_user`), une session par statut, un fichier, un point
    de reprise par session et un vecteur."""
    await seed_user(db, user_id, tag, app.state.cipher.encrypt(f"cle-{tag}"))
    sessions = [
        AgentSession(user_id=user_id, graph="demo_debate", status=status, input={})
        for status in statuses
    ]
    db.add_all(sessions)
    await db.commit()
    saver = saver_of(app)
    threads = [row.id for row in sessions]
    for thread in threads:
        await put_checkpoint(saver, thread)
    storage = app.state.memory_providers.storage
    files = [await storage.save(user_id, "documents", f"fichier-{tag}".encode(), ".txt")]
    chunk = make_chunk(user_id, f"texte {tag}")
    await app.state.memory_providers.index.index([chunk])
    return Footprint(user_id, files, threads, chunk)


async def seed_two_accounts(db: AsyncSession, app: FastAPI) -> tuple[Footprint, Footprint]:
    """Camille (le compte local de l'application) et Dominique, chacun avec ses traces."""
    await seed_other_user(db)
    mine = await seed_footprint(
        db, app, app.state.local_user_id, "camille", statuses=("completed",)
    )
    theirs = await seed_footprint(db, app, OTHER, "dominique", statuses=("completed", "running"))
    return mine, theirs


async def vector_count(app: FastAPI, user_id: str) -> int:
    records = await app.state.memory_providers.index.vectors(user_id, limit=1000)
    return len(records)


async def delete_account(client: httpx.AsyncClient, **kwargs: Any) -> httpx.Response:
    return await client.post(DELETE, json=BODY, **kwargs)


def me_of(app: FastAPI) -> str:
    """Camille, le compte local de l'application de test."""
    local: str = app.state.local_user_id
    return local


async def goals_of(db: AsyncSession, user_id: str) -> int:
    stmt = select(func.count()).select_from(Goal).where(Goal.user_id == user_id)
    return (await db.execute(stmt)).scalar_one()
