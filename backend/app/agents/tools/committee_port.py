"""Port of the simulated hiring committee (SPEC F19, D147). `app.agents` imports no feature
(contract 6): it describes here what the `hiring_committee` graph needs; the `applications`
feature implements it (`AgentCommitteeStore`, task 7.10).

The CV, the offer, the file, the personas' words and the profile are personal or untrusted data
(17.2, 17.4): never logged, neither here nor by the implementation.

- `context`: read-only; 404 `committee_not_found` if the run is not January's.
- `save_result`: **idempotent per session**: a node replayed after a stop (SPEC 9.4) rereads
  the outcome of its session, writes no second vote, summary or event. Stores
  the four votes, the verdict, the ranked objections and the three changes, moves the
  run to `done` and, if the offer has a record, adds the `committee` event to its thread."""

from typing import Protocol

from app.agents.tools.committee_schema import CommitteeContext, PersonaVote, Synthesis
from app.core.errors import AppError


class CommitteeStore(Protocol):
    async def context(self, user_id: str, run_id: str) -> CommitteeContext: ...

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None: ...


def committee_unavailable() -> AppError:
    return AppError(
        "committee_unavailable", "The hiring committee is unavailable in this runtime.", 503
    )


class _NoCommittee:
    """Engine default value (tests, starts without the feature)."""

    async def context(self, user_id: str, run_id: str) -> CommitteeContext:
        raise committee_unavailable()

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None:
        raise committee_unavailable()


NO_COMMITTEE: CommitteeStore = _NoCommittee()
