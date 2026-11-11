from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.run_settings import RunSettings


async def test_user_messages_since_returns_only_user_messages_after_seq(
    db_factory: async_sessionmaker[AsyncSession], bus: EventBus, user_id: str, session_id: str
) -> None:
    async def publish(type_: str, payload: dict[str, object]) -> int:
        event = await bus.publish(
            user_id=user_id,
            session_id=session_id,
            type=type_,
            payload=payload,  # type: ignore[arg-type]
        )
        return event.seq

    first = await publish("user.message", {"text": "un"})
    await publish("agent.message", {"message_id": "m", "text": "réponse"})
    third = await publish("user.message", {"text": "deux"})
    deps = GraphDeps(
        user_id=user_id,
        session_id=session_id,
        models=None,  # type: ignore[arg-type]
        bus=bus,
        settings=RunSettings(300_000, 3, "fr", ("fr", "en"), ""),
        session_factory=db_factory,
    )
    assert await deps.user_messages_since(0) == [(first, "un"), (third, "deux")]
    assert await deps.user_messages_since(first) == [(third, "deux")]
    assert await deps.user_messages_since(third) == []
