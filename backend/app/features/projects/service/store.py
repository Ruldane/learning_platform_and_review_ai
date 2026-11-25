"""Port of the `project_brief` and `project_review` flows (`ProjectStore`, D165, D166) on the
`projects` feature: implementation wired by `bootstrap_agents.agent_ports(..., projects=...)`.
Each call opens its own short database sessions; the repository read happens outside a
transaction.

Writes are **idempotent per session** (SPEC 9.4): the statement is only stored if it is still
absent, the evaluation only if this session has not already stored it (`review.save_review`).
The port has no "failed submission": an evaluation session that fails or is cancelled stores
nothing, and the `reviewing` status follows the session (`settle`): January can submit again.

Statement, submission, repository, criteria and drafts are January's or the web's data: never
logged (17.2); the logs carry ids, numbers and codes."""

import logging

from app.agents.tools.project_port import BriefInputs, DraftResult, ReviewInputs, ReviewOutcome
from app.agents.tools.project_schema import ProjectBrief
from app.core.errors import AppError
from app.features.ledger.service.ledger import safe_code
from app.features.projects.service import inputs
from app.features.projects.service.review import save_drafts, save_review
from app.features.projects.service.runtime import BRIEF_ATTEMPTS, ProjectsRuntime
from app.features.research.service.reading import read

logger = logging.getLogger(__name__)


class AgentProjectStore:
    def __init__(self, runtime: ProjectsRuntime) -> None:
        self._rt = runtime

    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs:
        return await inputs.brief_inputs(self._rt, user_id, project_id)

    async def save_brief(
        self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief
    ) -> None:
        """The statement, once only: the project becomes "to do" and takes its title."""
        async with self._rt.project_lock(user_id, project_id), self._rt.session_factory() as db:
            row = await inputs.owned(db, user_id, project_id)
            written = not row.brief and row.status in ("brief_pending", "brief_failed")
            if written:
                row.brief = brief.model_dump(mode="json")
                row.title = brief.title[:200]
                row.status, row.session_id = "todo", None
                await db.commit()
        logger.info(
            "Statement stored: session %s, project %s, first write %s",
            session_id,
            project_id,
            written,
        )

    async def brief_failed(self, user_id: str, session_id: str, project_id: str, code: str) -> None:
        """The statement failed: on the third try the project becomes `brief_failed`
        ("Retry"), before that, the task relaunches a try when the session is closed."""
        failed = False
        async with self._rt.project_lock(user_id, project_id), self._rt.session_factory() as db:
            row = await inputs.owned(db, user_id, project_id)
            if (
                row.status == "brief_pending"
                and not row.brief
                and row.brief_attempts >= BRIEF_ATTEMPTS
            ):
                row.status, row.session_id = "brief_failed", None
                await db.commit()
                failed = True
        logger.info(
            "Statement failed: session %s, project %s, code %s, final %s",
            session_id,
            project_id,
            safe_code(code),
            failed,
        )

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs:
        return await inputs.review_inputs(self._rt, user_id, project_id)

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None:
        """The text of a repository page (cache, per-domain rate, SSRF guard, excluded domains:
        those of the web search, outside a session); `None` if it cannot be read. Hook for
        phase 14 (GitHub)."""
        try:
            outcome = await read(self._rt.research, user_id, None, url)
        except (
            AppError
        ) as exc:  # link refused (`invalid_url`, `url_forbidden`): unreadable repository
            logger.info("Repository refused: user %s, code %s", user_id, safe_code(exc.code))
            return None
        return outcome.text if outcome.status == "ok" and outcome.text.strip() else None

    async def save_review(
        self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
    ) -> None:
        await save_review(self._rt, user_id, session_id, project_id, outcome)

    async def save_drafts(
        self, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
    ) -> bool:
        return await save_drafts(self._rt, user_id, session_id, project_id, drafts)
