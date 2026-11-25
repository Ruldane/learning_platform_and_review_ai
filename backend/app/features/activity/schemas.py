"""Activity feed contract (SPEC 14.2, P15, D163): what agents and background tasks have done,
with no invented content. The text is written by the code, never by a model."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ActivityKind = Literal["lesson", "radar", "brief", "memory", "project", "job_failed"]


class ActivityItem(BaseModel):
    """An event. `id` is stable (`{kind}:{ref}:{state}`): the front end does not show the same one
    twice; `link` is a front-end route."""

    id: str
    kind: ActivityKind
    at: datetime
    title: str
    detail: str | None = None
    link: str | None = None


class ActivityPage(BaseModel):
    """The events, most recent first. `latest_at`: the instant of the most recent of them
    (`None` with no event). Re-read cursor: `after` = `latest_at`, `after_id` = the `id` of the
    first item of `items`; older-page cursor: `at` and `id` of the last item."""

    items: list[ActivityItem]
    latest_at: datetime | None
