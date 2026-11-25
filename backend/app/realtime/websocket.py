"""WebSocket entry point of a session's stream: origin, ownership, then replay and live.

- **Origin**: CORS does not apply to WebSockets; a browser always sends `Origin`,
  which must be one of the allowed origins (`Settings.cors_origins`), otherwise the
  handshake is refused (close 1008 before `accept`: the browser itself only sees a 1006,
  as for an invalid `after_seq` or a 401). Without an `Origin` header (non-browser client,
  tests): accepted in local mode, **refused in Google mode** (1008, after the 401 of a
  connection without a valid cookie): the session cookie there is the key to an account.
- **Ownership**: unknown session or one belonging to another user -> accepted then closed with
  `4404` (a refusal before `accept` would only reach the browser as an anonymous 1006).
- **Database**: never a session kept open for the length of the connection (D38); each read
  (ownership, status, last `seq`) opens a short session through `session_factory`.
"""

from fastapi import WebSocketException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocket

from app.agents.runtime import control
from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.repositories import EventRepository
from app.core.errors import AppError
from app.realtime import replay

CLOSE_NOT_FOUND = 4404


async def check_origin(conn: HTTPConnection) -> None:
    """Dependency of the WebSocket route: refuses an origin outside `cors_origins`, and in
    Google mode a handshake without `Origin` (the 401 of a cookie-less connection comes first)."""
    origin = conn.headers.get("origin")
    if origin is None:
        if conn.app.state.settings.auth_mode == "google":
            await conn.app.state.authenticator.authenticate(conn)  # 401 `auth_required` first
            raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "Origin required.")
        return
    if origin.rstrip("/") not in conn.app.state.settings.cors_origins:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "Origin not allowed.")


async def serve_session_stream(
    ws: WebSocket, runtime: AgentRuntime, user_id: str, session_id: str, after_seq: int
) -> None:
    factory: async_sessionmaker[AsyncSession] = ws.app.state.session_factory
    await ws.accept()
    try:
        await control.get_owned(factory, user_id, session_id)
    except AppError:
        await ws.close(code=CLOSE_NOT_FOUND, reason="Session not found.")
        return

    await replay.stream_to_socket(
        ws,
        runtime.bus,
        user_id,
        session_id,
        after_seq,
        read_end_seq=end_seq_reader(factory, user_id, session_id),
    )


def end_seq_reader(
    factory: async_sessionmaker[AsyncSession], user_id: str, session_id: str
) -> replay.EndSeqReader:
    """End `seq` of the session (see `replay`): status read first, then the `seq` in another
    short session, so that it is at least as recent as the status."""

    async def read() -> int | None:
        try:
            status = (await control.get_owned(factory, user_id, session_id)).status
        except AppError:
            return 0  # session gone: nothing left to wait for
        if status not in control.TERMINAL:
            return None
        async with factory() as db:
            events = EventRepository(db, user_id)
            if status in ("cancelled", "expired"):  # no final event: everything that is written
                return await events.max_seq(session_id)
            # `completed` / `failed`: the final event, written in the same transaction as
            # the status (D61). `None` (row from before D61 without its event): open stream.
            return await events.last_seq_of(session_id, replay.FINAL_EVENTS)

    return read
