from datetime import datetime
from typing import Literal

from pydantic import BaseModel

BookFormat = Literal["pdf", "epub"]
BookStatus = Literal["not_requested", "queued", "ready", "failed"]


class BookOut(BaseModel):
    status: BookStatus
    available: bool = False
    chapters: int = 0
    rendered_at: datetime | None = None
