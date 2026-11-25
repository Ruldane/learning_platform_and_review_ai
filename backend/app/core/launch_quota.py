"""The cap on route launches through MCP (phase 10, M11): an agent route costs January's API,
and Claude can launch them through dozens of routes. The count is made **at the source**,
where the application starts a session (`SessionRunner.start`), when the call comes from
MCP: no route bypasses it, declared or not.

In-memory counter, per user, over a sliding 24 h window. A restart resets it (like the
per-minute MCP limits, D204: it grants no more right than a valid token already has).
`reserve` counts before the start, with no `await` between the check and the registration:
simultaneous calls never all pass; `release` gives back the slot of a refused launch before
it has started."""

from collections import deque
from datetime import UTC, datetime, timedelta

from app.core.errors import AppError

GRAPH_LAUNCHES_PER_DAY = 30
_WINDOW = timedelta(days=1)


class LaunchQuota:
    def __init__(self, limit: int = GRAPH_LAUNCHES_PER_DAY) -> None:
        self.limit = limit
        self._launches: dict[str, deque[datetime]] = {}

    def reserve(self, user_id: str, now: datetime | None = None) -> datetime:
        """Counts one more launch; returns its instant (for `release`). Above the cap:
        `mcp_graph_quota` (429), with no content; nothing is counted."""
        moment = now or datetime.now(UTC)
        launches = self._launches.setdefault(user_id, deque())
        while launches and launches[0] <= moment - _WINDOW:
            launches.popleft()
        if len(launches) >= self.limit:
            raise AppError(
                "mcp_graph_quota",
                f"The limit of {self.limit} workflow launches in a rolling 24-hour period "
                "has been reached. Try again later or ask January to start it in the app.",
                429,
                {"limit": self.limit, "window": "day"},
            )
        launches.append(moment)
        return moment

    def release(self, user_id: str, moment: datetime) -> None:
        """Gives back the slot of a launch that did not start."""
        launches = self._launches.get(user_id)
        if launches is not None and moment in launches:
            launches.remove(moment)
