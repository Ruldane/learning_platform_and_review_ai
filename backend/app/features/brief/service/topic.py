"""The brief resource topic (F17, D161): "{target field} news", built by the code, never by a
model. The field comes, in order, from: the radar settings role, the latest goal's role, a short
topic taken from that goal's text (a leading "Devenir" or "Become" removed, a single line,
`MAX_TOPIC` characters at most), then the validated program title. None of these: `None`, no
search. The topic is request and prompt data (framed `untrusted`); it is never logged."""

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.service.goals import list_goals
from app.features.program.service.programs import list_programs
from app.features.radar.service.runs import defaults

TOPIC_SUFFIX = "news"
MAX_TOPIC = 80  # characters of the field taken from free text

_VERB = re.compile(
    r"^(?:devenir|become)\b\s*(?:(?:une?|le|la|les|an?|the)\b\s*|l['’]\s*)?", re.IGNORECASE
)
_SENTENCE_END = re.compile(r"[.!?;:]")


def _cap(text: str) -> str:
    """`text` cut at `MAX_TOPIC` characters, on a word boundary if possible."""
    if len(text) <= MAX_TOPIC:
        return text
    head = text[:MAX_TOPIC]
    return head.rsplit(" ", 1)[0] if " " in head else head


def goal_topic(text: str) -> str | None:
    """A short topic taken from a goal's free text: a single line, without the verb "Devenir" or
    "Become" nor the article that follows, cut at the first sentence then at `MAX_TOPIC`
    characters (on a word). `None` if nothing is left."""
    line = _VERB.sub("", " ".join(text.split()), count=1)
    return _cap(_SENTENCE_END.split(line, maxsplit=1)[0].strip()).strip() or None


async def resource_topic(db: AsyncSession, user_id: str) -> str | None:
    """The search topic of the day's resource, `None` if no field is known."""
    role, _zone = await defaults(db, user_id)
    if role:
        return f"{role} {TOPIC_SUFFIX}"
    goals = await list_goals(db, user_id)
    if goals and (topic := goal_topic(goals[0].text)) is not None:
        return f"{topic} {TOPIC_SUFFIX}"
    programs = await list_programs(db, user_id)
    current = next((p for p in programs if p.status == "validated"), None)
    title = " ".join(current.title.split()) if current is not None else ""
    return f"{title} {TOPIC_SUFFIX}" if title else None
