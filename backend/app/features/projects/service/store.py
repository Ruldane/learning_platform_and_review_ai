"""Port des parcours `project_brief` et `project_review` (`ProjectStore`, D165, D166) sur la feature
`projects` : implémentation branchée par `bootstrap_agents.agent_ports(..., projects=...)`. Chaque
appel ouvre ses propres sessions de base, courtes ; la lecture du dépôt se fait hors transaction.

Les écritures sont **idempotentes par session** (SPEC 9.4) : l'énoncé n'est rangé que s'il est
encore absent, l'évaluation que si cette session ne l'a pas déjà rangée (`review.save_review`).
Le port n'a pas de « rendu en échec » : une session de l'évaluation qui échoue ou est annulée
ne range rien, et le statut `reviewing` suit la session (`settle`) : January peut rendre de nouveau.

Énoncé, rendu, dépôt, critères et brouillons sont des données de January ou du web : jamais
journalisés (17.2) ; les journaux portent des identifiants, des nombres et des codes."""

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
        """L'énoncé, une seule fois : le projet passe à « à faire » et prend son titre."""
        async with self._rt.project_lock(user_id, project_id), self._rt.session_factory() as db:
            row = await inputs.owned(db, user_id, project_id)
            written = not row.brief and row.status in ("brief_pending", "brief_failed")
            if written:
                row.brief = brief.model_dump(mode="json")
                row.title = brief.title[:200]
                row.status, row.session_id = "todo", None
                await db.commit()
        logger.info(
            "Énoncé rangé : session %s, projet %s, première écriture %s",
            session_id,
            project_id,
            written,
        )

    async def brief_failed(self, user_id: str, session_id: str, project_id: str, code: str) -> None:
        """L'énoncé a échoué : à la troisième tentative le projet passe en `brief_failed`
        (« Réessayer »), avant, la tâche relance un essai quand la session est close."""
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
            "Énoncé en échec : session %s, projet %s, code %s, définitif %s",
            session_id,
            project_id,
            safe_code(code),
            failed,
        )

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs:
        return await inputs.review_inputs(self._rt, user_id, project_id)

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None:
        """Le texte d'une page du dépôt (cache, débit par domaine, garde SSRF, domaines exclus :
        ceux de la recherche web, hors session) ; `None` si elle ne se lit pas. Point d'accroche
        de la phase 14 (GitHub)."""
        try:
            outcome = await read(self._rt.research, user_id, None, url)
        except AppError as exc:  # lien refusé (`invalid_url`, `url_forbidden`) : dépôt illisible
            logger.info("Dépôt refusé : utilisateur %s, code %s", user_id, safe_code(exc.code))
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
