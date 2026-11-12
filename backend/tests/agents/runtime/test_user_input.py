"""Entrées de l'utilisatrice lues par les nœuds (D82) : texte et commande du débat."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.user_input import UserInput, user_input_of


def _deps(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, uid: str, sid: str
) -> GraphDeps:
    return GraphDeps(
        user_id=uid,
        session_id=sid,
        models=None,  # type: ignore[arg-type]
        bus=bus,
        settings=RunSettings(300_000, 3, "fr", ("fr",), ""),
        session_factory=db_factory,
    )


async def test_user_inputs_since_returns_commands(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    async def publish(type_: str, payload: dict[str, object]) -> int:
        event = await bus.publish(
            user_id=user_id,
            session_id=session_id,
            type=type_,  # type: ignore[arg-type]
            payload=payload,
        )
        return event.seq

    first = await publish("user.message", {"text": "", "command": "shorter"})
    await publish("agent.message", {"message_id": "m", "text": "réponse"})
    third = await publish("user.message", {"text": "Plus de pratique", "command": None})
    fourth = await publish("user.message", {"text": "ancien format"})
    deps = _deps(db_factory, bus, user_id, session_id)
    assert await deps.user_inputs_since(0) == [
        UserInput(first, "", "shorter"),
        UserInput(third, "Plus de pratique", None),
        UserInput(fourth, "ancien format", None),
    ]
    assert await deps.user_inputs_since(third) == [UserInput(fourth, "ancien format", None)]
    # La démo lit toujours le texte seul.
    assert await deps.user_messages_since(0) == [
        (first, ""),
        (third, "Plus de pratique"),
        (fourth, "ancien format"),
    ]


def test_user_input_of_ignores_an_unknown_command() -> None:
    """Charge stockée hors catalogue (écrite à la main, version future) : texte gardé, commande
    ignorée plutôt qu'une erreur au milieu d'un tour."""
    assert user_input_of(4, {"text": "x", "command": "louder"}) == UserInput(4, "x", None)
    assert user_input_of(5, {}) == UserInput(5, "", None)
    assert user_input_of(6, {"command": "to_proposals"}) == UserInput(6, "", "to_proposals")
