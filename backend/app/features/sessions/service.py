"""Agent sessions on the API side: reads through the feature's repository, actions through the
runner (which opens its own short database sessions and applies the status rules, D46)."""

import builtins
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.events import (
    InterruptRequestedPayload,
    RunFailedPayload,
    SessionEvent,
)
from app.agents.runtime.handle import AgentRuntime
from app.agents.tools.boss_port import BOSS_GRAPH
from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.agents.tools.expert_debate_port import EXPERT_GRAPH
from app.core.errors import AppError
from app.db.models.agents import AgentSession, SessionStatus
from app.features.sessions.play_service import expire_steps
from app.features.sessions.repository import SessionReadRepository
from app.features.sessions.schemas import (
    MessageRequest,
    ResumeRequest,
    SessionView,
    StartSessionRequest,
)

# Other features go through this service (contract 2): queries and view re-exported.
__all__ = [
    "MessageRequest",
    "ResumeRequest",
    "SessionFacts",
    "SessionView",
    "SessionsService",
    "expire_steps",
    "find_active_session",
    "find_latest_session",
    "list_open_sessions",
    "list_open_sessions_by_subject",
    "session_facts",
    "to_view",
]


# Workflows launched only by their feature's route, which checks the subject and concurrency
# (D106: one replan per program, program validated; 409 `replan_open`; quiz and study
# session: lock, subject and feature row, final review of phase 5).
ROUTE_ONLY: dict[str, str] = {
    BOSS_GRAPH: "POST /boss/programs/{program_id}/submit",
    CONVERSATION_GRAPH: "POST /lessons/{lesson_id}/conversation/messages",
    EXPERT_GRAPH: "POST /expert-debates",
    "replan": "POST /programs/{program_id}/replan",
    "capture": "POST /capture",
    "quiz": "POST /modules/{module_id}/quiz",
    "study_session": "POST /study-sessions",
    "gap_analysis": "POST /postings",  # the posting is created and checked by its route (D121)
    "cv_capture": "POST /profile/import or POST /cv/templates",  # documents stored first (D124)
    "application_intake": "POST /applications/intake",  # a single open session (D141)
    "application_kit": "POST /applications/{id}/kit",  # checked record, pieces kept (D142)
    "interview": "POST /applications/{id}/interviews",  # interview and settings checked (D145)
    "hiring_committee": "POST /committee",  # CV version ready, one committee per posting (D147)
    "daily_brief": "GET /brief/today",  # brief created and opened by its route (D161)
    "lesson_update": "Lesson watch scheduler",
    "linkedin_draft": "POST /linkedin-drafts",
    "lesson_hunt": "POST /lesson-hunts",
    "skill_transfer": "POST /skill-transfers/{transfer_id}/prepare",
    "blind_assessment": "POST /blind-assessments/{assessment_id}/evaluate",
    "recruitment_process": "POST /recruitment-processes/{process_id}/steps/{kind}/answers",
    "grade_appeals": "POST /grade-appeals/{appeal_id}/review",
    "paper_lab": "POST /paper-labs",
    "podcast": "POST /podcast/today",
    "market_radar": "POST /radar/runs",  # run created, role and area set by its route (D159)
    "project_brief": "scheduler or POST /projects/{id}/brief",  # module brief (D165)
    # submission checked then reviewed (D165); drafts of a validated project (D181)
    "project_review": "POST /projects/{id}/submit or POST /projects/{id}/drafts",
    # teacher cost barrier (triggers, caps, anti-repetition), then exercises
    # checked in the sandbox (D203)
    "ide_teacher": "POST /ide/sessions/{id}/teach",
    "ide_exercise": "POST /ide/exercises/generate",
    "code_trial": "POST /ide/sessions/{session_id}/code-trials",
    "oncall_review": "POST /oncall/incidents/{id}/report",
    "cv_review": "POST /cv/reviews",  # profile, template and posting checked then frozen (D130)
}


def to_view(row: AgentSession, last_seq: int) -> SessionView:
    pending = row.pending_interrupt
    return SessionView(
        id=row.id,
        graph=row.graph,
        played_by=row.played_by,
        status=row.status,  # type: ignore[arg-type]  # colonne texte, valeurs de SessionStatus
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        last_seq=last_seq,
        pending_interrupt=InterruptRequestedPayload.model_validate(pending) if pending else None,
        error=RunFailedPayload.model_validate(row.error) if row.error else None,
        tokens_in=row.tokens_in,
        tokens_out=row.tokens_out,
        cost_usd=row.cost_usd,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def find_active_session(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str, subject_id: str
) -> str | None:
    """Most recent session of `graph` on this subject that is still open (`running`,
    `waiting_user` or `paused`), `None` otherwise. Read for other features (contract 2)."""
    return await SessionReadRepository(db, user_id).latest_open(
        graph=graph, subject_type=subject_type, subject_id=subject_id
    )


async def list_open_sessions(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str, subject_id: str
) -> builtins.list[str]:
    """All open sessions of `graph` on this subject (lesson production: one chain per
    program, D91). Read for other features (contract 2)."""
    return await SessionReadRepository(db, user_id).open_ids(
        graph=graph, subject_type=subject_type, subject_id=subject_id
    )


async def list_open_sessions_by_subject(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str
) -> builtins.dict[str, builtins.list[str]]:
    """Open sessions of `graph` on all subjects of one type, by `subject_id`, in a single
    query (lists without N+1). Read for other features (contract 2)."""
    return await SessionReadRepository(db, user_id).open_ids_by_subject(
        graph=graph, subject_type=subject_type
    )


async def find_latest_session(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str, subject_id: str
) -> str | None:
    """Most recent session of `graph` on this subject, whatever its status, `None` if there
    is none. Read for other features (contract 2)."""
    return await SessionReadRepository(db, user_id).latest(
        graph=graph, subject_type=subject_type, subject_id=subject_id
    )


@dataclass(frozen=True)
class SessionFacts:
    status: str
    input: dict[str, Any]
    pending: dict[str, Any] | None = None  # question en attente (`InterruptRequestedPayload`)
    played_by: str | None = None
    model_provider: str | None = None


async def session_facts(db: AsyncSession, user_id: str, session_id: str) -> SessionFacts | None:
    """Status and input of one of the user's sessions (retry of a failed workflow, D97),
    `None` if it does not exist. Read for other features (contract 2)."""
    row = await SessionReadRepository(db, user_id).get(session_id)
    if row is None:
        return None
    return SessionFacts(
        row.status, dict(row.input or {}), row.pending_interrupt, row.played_by, row.model_provider
    )


class SessionsService:
    def __init__(self, db: AsyncSession, user_id: str, runtime: AgentRuntime) -> None:
        self._repo = SessionReadRepository(db, user_id)
        self._user_id = user_id
        self._runner = runtime.runner

    async def start(self, req: StartSessionRequest) -> str:
        """Creates the session and runs the workflow in the background: returns at once. A
        workflow that has its own route (`ROUTE_ONLY`) is sent there (409 `graph_has_route`)."""
        if req.graph in ROUTE_ONLY:
            raise AppError(
                "graph_has_route",
                "This workflow is started from its own screen.",
                409,
                {"graph": req.graph, "route": ROUTE_ONLY[req.graph]},
            )
        return await self._runner.start(
            self._user_id, req.graph, req.input, req.subject_type, req.subject_id
        )

    async def get(self, session_id: str) -> SessionView:
        """The last `seq` is read BEFORE the row: the returned status is therefore at least as
        recent as `last_seq`, and the front can order this read and the events (D56)."""
        seqs = await self._repo.last_seqs([session_id])
        row = await self._repo.get(session_id)
        if row is None:
            raise AppError("session_not_found", "Session not found.", 404)
        return to_view(row, seqs.get(session_id, 0))

    async def list(
        self, graph: str | None, status: SessionStatus | None
    ) -> builtins.list[SessionView]:
        rows = await self._repo.list_recent(graph=graph, status=status)
        seqs = await self._repo.last_seqs([row.id for row in rows])
        return [to_view(row, seqs.get(row.id, 0)) for row in rows]

    async def resume(self, session_id: str, req: ResumeRequest) -> SessionView:
        await self._runner.resume(self._user_id, session_id, req.interrupt_id, req.value)
        return await self.get(session_id)

    async def message(self, session_id: str, req: MessageRequest) -> SessionEvent:
        """Publishes the message (text trimmed) and its command; nothing to say and nothing to
        command: 422, path `text` only, never the input."""
        text = req.text.strip()
        if not text and req.command is None:
            raise AppError(
                "invalid_input",
                "Write a message or choose a command.",
                422,
                {"fields": ["text"]},
            )
        return await self._runner.post_message(self._user_id, session_id, text, req.command)

    async def pause(self, session_id: str) -> SessionView:
        await self._runner.pause(self._user_id, session_id)
        return await self.get(session_id)

    async def cancel(self, session_id: str) -> SessionView:
        await self._runner.cancel(self._user_id, session_id)
        return await self.get(session_id)
