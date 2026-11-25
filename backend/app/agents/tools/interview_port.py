"""Port de l'entretien blanc (SPEC F10, D145). `app.agents` n'importe aucune feature (contrat 6) :
il décrit ici ce dont le parcours `interview` a besoin ; la feature `applications` l'implémente
(`AgentInterviewStore`, tâche 7.9).

Les réponses de January, l'offre, le profil et le dossier sont des données personnelles ou non
fiables (17.2, 17.4) : jamais journalisés, ni ici ni par l'implémentation.

- `context` : lecture seule ; 404 `interview_not_found` si l'entretien n'est pas à January.
- `save_result` : **idempotent par session** : un nœud rejoué après un arrêt (SPEC 9.4) relit
  l'issue de sa session, n'écrit ni second débrief ni seconde fiche. `debrief=None` et
  `exchanges=[]` : entretien arrêté avant la première réponse (`stopped`, rien d'autre : ni
  échange, ni fiche, ni événement) ; `debrief=None` avec des échanges : le débrief a échoué,
  entretien `debrief_failed` (les réponses sont gardées, ni fiche, ni événement de débrief) ;
  sinon entretien `done` avec ses échanges, son débrief, les termes que le profil ne
  dit pas dans la réponse améliorée (`flags` : réponse « à vérifier ») et les fiches de révision
  des questions ratées (source `interview`)."""

from typing import Protocol

from app.agents.tools.interview_schema import Debrief, Exchange, InterviewContext
from app.agents.tools.study_schema import CardDraft
from app.agents.tools.system_design_port import (
    SystemDesignContext,
    SystemDesignReview,
    SystemDesignSubmission,
)
from app.core.errors import AppError


class InterviewStore(Protocol):
    async def freeze_design(
        self, user_id: str, session_id: str, interview_id: str, submission: SystemDesignSubmission
    ) -> SystemDesignContext: ...

    async def save_design_review(
        self, user_id: str, session_id: str, interview_id: str, review: SystemDesignReview
    ) -> None: ...

    async def context(self, user_id: str, interview_id: str) -> InterviewContext: ...

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        interview_id: str,
        exchanges: list[Exchange],
        debrief: Debrief | None,
        flags: list[str],
        cards: list[CardDraft],
    ) -> None: ...


def interview_unavailable() -> AppError:
    return AppError(
        "interview_unavailable", "Mock interviews are unavailable in this runtime.", 503
    )


class _NoInterviews:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def freeze_design(
        self, user_id: str, session_id: str, interview_id: str, submission: SystemDesignSubmission
    ) -> SystemDesignContext:
        raise interview_unavailable()

    async def save_design_review(
        self, user_id: str, session_id: str, interview_id: str, review: SystemDesignReview
    ) -> None:
        raise interview_unavailable()

    async def context(self, user_id: str, interview_id: str) -> InterviewContext:
        raise interview_unavailable()

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
        raise interview_unavailable()


NO_INTERVIEWS: InterviewStore = _NoInterviews()
