"""Port of the daily brief (P11, D161). `app.agents` imports no feature (contract 6): it describes
here what the `daily_brief` flow needs; the `brief` feature implements it (task 8.6).

The brief is a snapshot of the day: the block, reviews, follow-ups, offers and progress are
**computed by code** (`brief` feature); only the resource (the Scout) and the two advice sentences
(the Moderator) go through a model. The day's facts, the topic and the stored texts are user or web
data (17.2, 17.4): never logged.

- `context`: read only; the day's facts, what is already stored (`resource_done`, `advice_done`)
  and the numbers the advice may quote (`allowed_numbers`, computed by code from the facts).
- `save_resource`: the day's resource, `None` = empty section (no topic, no readable page, search
  down). Idempotent: the first write wins, a replayed node changes nothing.
- `save_advice`: the two advice sentences, `None` = `failed` advice (an invented number, or no
  valid answer), or `unavailable` (`unavailable=True`: no model, for lack of a key). Idempotent
  too; advice stored as `None` stays so all day (never retried)."""

from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

from app.agents.tools.brief_schema import ResourceView
from app.core.errors import AppError

# Error codes of the model factory when no model can be built (no key, unreadable key, unknown
# provider): the advice is then "unavailable", not "failed".
MODEL_UNAVAILABLE_CODES = frozenset(
    {"llm_key_missing", "llm_key_unreadable", "llm_provider_unknown"}
)


@dataclass(frozen=True)
class AdviceFacts:
    """The day's facts, as counted by code. The advice says nothing else."""

    # A `None` fact: its section was down this morning (`unavailable`); the advice does not receive
    # it, never a replacement zero. `block_minutes` `None`: the block is unavailable.
    block_title: str | None  # the day's study block (`None`: no block planned)
    block_minutes: int | None
    cards_due: int | None  # cards to review
    reminders_due: int | None  # application follow-ups due
    offers: int | None  # offers to look at
    best_score: int | None  # best recent quiz score
    week_planned: int | None  # tasks planned this week
    week_done: int | None  # tasks done this week
    streak_days: int | None  # consecutive study days


@dataclass(frozen=True)
class BriefContext:
    brief_id: str
    day: date
    language: Literal["fr", "en"]
    topic: str | None  # the resource topic (`None`: no search)
    facts: AdviceFacts
    resource_done: bool
    advice_done: bool
    allowed_numbers: frozenset[str]  # numbers allowed in the advice (canonical form)


class BriefStore(Protocol):
    async def context(self, user_id: str, brief_id: str) -> BriefContext: ...

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None: ...

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None: ...


def brief_unavailable() -> AppError:
    return AppError("brief_unavailable", "The daily brief is not wired to this engine.", 503)


class _NoBrief:
    """Engine default (tests, startups without the feature)."""

    async def context(self, user_id: str, brief_id: str) -> BriefContext:
        raise brief_unavailable()

    async def save_resource(
        self, user_id: str, session_id: str, brief_id: str, resource: ResourceView | None
    ) -> None:
        raise brief_unavailable()

    async def save_advice(
        self,
        user_id: str,
        session_id: str,
        brief_id: str,
        sentences: list[str] | None,
        *,
        unavailable: bool = False,
    ) -> None:
        raise brief_unavailable()


NO_BRIEF: BriefStore = _NoBrief()
