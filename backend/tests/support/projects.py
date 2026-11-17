"""Faux port des projets preuves (`FakeProjectStore`) en mémoire, idempotent par session comme le
contrat (D165) : la première écriture gagne, les suivantes sont comptées sans rien changer. Aucun
réseau ni LLM. Identité fictive « Camille Exemple », dépôt `example.org`."""

from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.project_port import BriefInputs, DraftResult, ReviewInputs, ReviewOutcome
from app.agents.tools.project_schema import ProjectBrief
from tests.support.cv_review import profile

PROJECT_ID = "00000000-0000-4000-8000-0000000000c1"
REPO_URL = "https://example.org/camille/suivi-lecture"
README = "# Suivi de lecture\nUne API de suivi de lecture, avec des tests."
DESCRIPTION = "J'ai construit une API de suivi de lecture avec FastAPI et Pydantic, avec des tests."
TITLE = "Une API de suivi de lecture"
CRITERIA = [
    "Le dépôt expose au moins trois routes documentées.",
    "Les entrées sont validées par des modèles Pydantic.",
    "Le dépôt contient des tests qui passent.",
    "La description dit comment lancer le projet.",
]


def sample_brief(**over: Any) -> ProjectBrief:
    data: dict[str, Any] = {
        "title": TITLE,
        "context": "Une petite équipe veut suivre ses lectures.",
        "objective": "Construire une API de suivi de lecture.",
        "constraints": ["Utiliser FastAPI.", "Aucun service payant."],
        "criteria": CRITERIA,
        "hours": 4,
        "deliverable": "either",
    }
    return ProjectBrief(**(data | over))


def brief_inputs(**over: Any) -> BriefInputs:
    data: dict[str, Any] = {
        "module_title": "Construire une API avec FastAPI",
        "skills": ["FastAPI", "Pydantic"],
        "prerequisites": ["Python"],
        "lesson_excerpt": "Une route FastAPI se déclare avec un décorateur.",
        "week_deliverable": "Une API documentée",
        "role": "Développeuse Python",
        "language": "fr",
    }
    return BriefInputs(**(data | over))


def review_inputs(**over: Any) -> ReviewInputs:
    data: dict[str, Any] = {
        "title": TITLE,
        "brief": sample_brief(),
        "repo_url": REPO_URL,
        "description": DESCRIPTION,
        "screenshots": 2,
        "skills": ["FastAPI", "Pydantic"],
        "profile": profile(skills=["Python"]),
        "language": "fr",
    }
    return ReviewInputs(**(data | over))


@dataclass
class FakeProjectStore:
    brief: BriefInputs = field(default_factory=brief_inputs)
    review: ReviewInputs = field(default_factory=review_inputs)
    readme: str | None = README  # ce que `repo_text` rend (`None` : page illisible)
    repo_error: Exception | None = None  # panne brute du lecteur
    saved_brief: ProjectBrief | None = None
    brief_saves: int = 0  # appels à `save_brief` (la première écriture gagne)
    failed_codes: list[str] = field(default_factory=list)
    outcome: ReviewOutcome | None = None
    review_saves: int = 0
    repo_calls: list[str] = field(default_factory=list)
    drafts: list[DraftResult] | None = None  # `save_drafts` : la première écriture gagne
    drafts_saves: int = 0

    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs:
        return self.brief

    async def save_brief(
        self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief
    ) -> None:
        self.brief_saves += 1
        if self.saved_brief is None:
            self.saved_brief = brief

    async def brief_failed(self, user_id: str, session_id: str, project_id: str, code: str) -> None:
        self.failed_codes.append(code)

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs:
        return self.review

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None:
        self.repo_calls.append(url)
        if self.repo_error is not None:
            raise self.repo_error
        return self.readme

    async def save_review(
        self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
    ) -> None:
        self.review_saves += 1
        if self.outcome is None:
            self.outcome = outcome

    async def save_drafts(
        self, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
    ) -> None:
        self.drafts_saves += 1
        if self.drafts is None:
            self.drafts = drafts
