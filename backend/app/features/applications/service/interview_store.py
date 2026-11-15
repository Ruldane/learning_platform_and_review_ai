"""Port de l'entretien blanc (`InterviewStore`, D145, D146) sur la feature `applications` :
implémentation branchée par `bootstrap_agents.agent_ports(..., interviews=...)`. Chaque appel ouvre
sa propre session de base, courte.

- `context` : lecture seule (`interview_context`). 404 `interview_not_found` (l'entretien n'est pas
  à l'utilisatrice), 409 `profile_required`.
- `save_result` : **idempotent par session**, sous le verrou des entretiens : un entretien qui n'est
  plus `running` (rejeu après un arrêt, SPEC 9.4) n'est jamais réécrit. `debrief=None` sans
  échange : `stopped` (rien d'autre) ; `debrief=None` avec des échanges : `debrief_failed`
  (réponses gardées, ni débrief, ni fiche, ni événement) ; sinon `done` : échanges, débrief (avec
  `flags` et `cards_created`, rangés avec lui), fiches de révision (`quiz.service.cards.add_cards`,
  source `interview`, dues demain, jamais de compétence : le texte vient du modèle) et, si
  l'entretien a une fiche, l'événement `interview` du fil, dans la même transaction.

Journaux : identifiants, statuts et nombres seulement (17.2)."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.interview_schema import Debrief, Exchange, InterviewContext
from app.agents.tools.study_schema import CardDraft
from app.core.clock import local_today
from app.db.models.applications import Interview
from app.features.applications.repository import ApplicationRepository, EventRepository
from app.features.applications.service.interview_context import build_context
from app.features.applications.service.interviews import interview_lock, interview_row
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.postings.service.duplicates import zone_of
from app.features.quiz.service.cards import NewCard, add_cards

logger = logging.getLogger(__name__)

MODE_LABELS = {
    "behavioral": "comportemental",
    "technical": "technique",
    "case": "étude de cas",
    "mixed": "mixte",
}


def timeline_text(row: Interview, cards: int) -> str:
    label = MODE_LABELS.get(row.mode, row.mode)
    return (
        f"Entretien blanc ({label}, {row.duration_min} min) terminé : débrief disponible, "
        f"{cards} fiche(s) de révision créée(s)."
    )


class AgentInterviewStore:
    def __init__(self, runtime: ApplicationsRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, interview_id: str) -> InterviewContext:
        async with self._rt.session_factory() as db:
            row = await interview_row(db, user_id, interview_id)
        return await build_context(self._rt, user_id, row)

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        interview_id: str,
        exchanges: list[Exchange],
        debrief: Debrief | None,
        flags: list[str],
        cards: list[CardDraft],
    ) -> None:
        rt = self._rt
        async with interview_lock(rt, user_id), rt.session_factory() as db:
            row = await interview_row(db, user_id, interview_id)
            if row.status != "running":
                return  # rejeu : l'issue de la session est déjà rangée
            row.exchanges = [item.model_dump(mode="json") for item in exchanges]
            created = 0
            if debrief is None:
                row.status = "debrief_failed" if exchanges else "stopped"
            else:
                created = await self._write_debrief(db, user_id, row, debrief, flags, cards)
            await db.commit()
            status = row.status
        logger.info(
            "Entretien rangé : utilisateur %s, entretien %s, session %s, statut %s, "
            "%d échange(s), %d fiche(s)",
            user_id,
            interview_id,
            session_id,
            status,
            len(exchanges),
            created,
        )

    async def _write_debrief(
        self,
        db: AsyncSession,
        user_id: str,
        row: Interview,
        debrief: Debrief,
        flags: list[str],
        cards: list[CardDraft],
    ) -> int:
        """Débrief, fiches de révision et événement du fil ; rend le nombre de fiches créées."""
        rt = self._rt
        today = local_today(await zone_of(db, user_id), rt.now())
        new = [NewCard(c.front, c.back, None, None, "interview", row.id) for c in cards]
        created = await add_cards(db, user_id, new, today)
        row.debrief = {
            **debrief.model_dump(mode="json"),
            "flags": list(flags),
            "cards_created": created,
        }
        row.status = "done"
        application = None
        if row.application_id is not None:
            application = await ApplicationRepository(db, user_id).get(row.application_id)
        if application is not None:
            await EventRepository(db, user_id).add(
                application_id=application.id,
                kind="interview",
                at=rt.now(),
                text=timeline_text(row, created),
                ref_id=row.id,
            )
        return created
