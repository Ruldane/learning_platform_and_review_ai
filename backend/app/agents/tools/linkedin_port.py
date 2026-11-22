from dataclasses import dataclass
from typing import Protocol

from app.agents.tools.linkedin_profile import LinkedInText

GRAPH = "linkedin_draft"


@dataclass(frozen=True)
class LinkedInContext:
    facts: dict[str, str]
    skills: tuple[str, ...]
    target_terms: tuple[str, ...]
    finished: bool


class LinkedInStore(Protocol):
    async def context(self, user_id: str, session_id: str, draft_id: str) -> LinkedInContext: ...

    async def propose(
        self, user_id: str, session_id: str, draft_id: str, text: LinkedInText
    ) -> None: ...


class _UnwiredLinkedIn:
    async def context(self, user_id: str, session_id: str, draft_id: str) -> LinkedInContext:
        raise RuntimeError("La rédaction LinkedIn n’est pas branchée.")

    async def propose(
        self, user_id: str, session_id: str, draft_id: str, text: LinkedInText
    ) -> None:
        raise RuntimeError("La rédaction LinkedIn n’est pas branchée.")


NO_LINKEDIN: LinkedInStore = _UnwiredLinkedIn()
