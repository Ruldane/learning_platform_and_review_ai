"""Matériel des tests des projets (D166) : l'app réelle (lifespan, vrais runtimes), un programme
validé de deux semaines écrit par le vrai port du Stratège (`tests.features.study.conftest.seed`),
des projets posés directement en base, un lanceur qui écrit la session `running` sans faire tourner
de graphe, une horloge figée. Aucun réseau ni LLM. Données fictives (« Camille Exemple »)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI
from sqlalchemy import select, update

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.project_port import DraftResult, ReviewOutcome
from app.agents.tools.project_schema import CriterionResult, ProfileEntryDraft
from app.db.models.career import MasterProfile
from app.db.models.daily import Project
from app.db.models.skills import Skill, UserSkill
from app.features.projects.service.runtime import ProjectsRuntime
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.study.conftest import Seeded
from tests.support.cv_review import profile
from tests.support.projects import DESCRIPTION, REPO_URL, TITLE, sample_brief

API = "/api/v1/projects"
WEEK_2 = datetime(
    2026, 11, 24, 10, 0, tzinfo=UTC
)  # mardi, 11 h à Paris : deux modules ont commencé
WEEK_1 = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)  # mardi de la semaine 1 : un seul module
NOW = WEEK_2

PNG = b"\x89PNG\r\n\x1a\n" + b"image-factice" * 8
JPEG = b"\xff\xd8\xff\xe0" + b"image-factice" * 8
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"image-factice" * 8
SUBMISSION: dict[str, Any] = {"repo_url": REPO_URL, "description": DESCRIPTION}
_SENTENCE = "Chaque route valide ses entrées avant de répondre, ce qui m'a appris les modèles."
# Un post LinkedIn de 80 à 200 mots, dit avec ce que January a dit de son projet : aucun terme à
# vérifier.
CLEAN_POST = " ".join(
    ["J'ai construit une API de suivi de lecture avec FastAPI et Pydantic, avec des tests."]
    + [_SENTENCE] * 5
)


@dataclass
class Env:
    app: FastAPI
    user_id: str
    launcher: RecordingLauncher
    seeded: Seeded

    @property
    def rt(self) -> ProjectsRuntime:
        runtime: ProjectsRuntime = self.app.state.daily.projects
        return runtime

    @property
    def modules(self) -> list[str]:
        return self.seeded.modules

    def at(self, moment: datetime) -> None:
        self.rt.now = lambda: moment

    @staticmethod
    def _brief(brief: bool | dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(brief, dict):
            return brief
        return sample_brief().model_dump(mode="json") if brief else None

    def last_submission(self) -> dict[str, Any]:
        """Un rendu tel que le rangent les routes (un lien, une description, sans capture)."""
        return {
            "at": NOW.isoformat(),
            "repo_url": REPO_URL,
            "description": DESCRIPTION,
            "screenshots": [],
        }

    async def add_project(
        self,
        module: int = 0,
        *,
        status: str = "todo",
        brief: bool | dict[str, Any] = True,
        user: str | None = None,
        **over: Any,
    ) -> str:
        """Un projet du module `module` (rang dans le programme semé), tel que le laisse un
        énoncé écrit (`todo`) ou, avec `brief=False`, en attente de son énoncé."""
        fields: dict[str, Any] = {
            "user_id": user or self.user_id,
            "module_id": self.modules[module],
            "program_id": self.seeded.program_id,
            "title": TITLE,
            "brief": self._brief(brief),
            "status": status,
            "submissions": [],
            "drafts": {},
        }
        async with self.app.state.session_factory() as db:
            row = Project(**(fields | over))
            db.add(row)
            await db.commit()
            return row.id

    async def row(self, project_id: str) -> Project:
        async with self.app.state.session_factory() as db:
            return (await db.execute(select(Project).where(Project.id == project_id))).scalar_one()

    async def projects(self) -> list[Project]:
        async with self.app.state.session_factory() as db:
            rows = await db.execute(select(Project).order_by(Project.created_at, Project.id))
            return list(rows.scalars())

    async def patch(self, project_id: str, **values: Any) -> None:
        async with self.app.state.session_factory() as db:
            await db.execute(update(Project).where(Project.id == project_id).values(**values))
            await db.commit()

    async def levels(self, *names: str) -> dict[str, tuple[str, set[str]]]:
        """`nom → (niveau, genres de preuves)` des compétences données."""
        out: dict[str, tuple[str, set[str]]] = {}
        async with self.app.state.session_factory() as db:
            stmt = (
                select(Skill.name, UserSkill.level, UserSkill.evidence)
                .join(UserSkill, UserSkill.skill_id == Skill.id)
                .where(Skill.user_id == self.user_id, Skill.name.in_(names))
            )
            for name, level, evidence in (await db.execute(stmt)).all():
                out[name] = (level, {str(item["kind"]) for item in evidence})
        return out

    async def add_profile(self, versions: int = 3, **over: Any) -> None:
        """`versions` versions validées du profil maître (la dernière : la courante)."""
        data: MasterProfileData = profile(skills=["Python"], **over)
        async with self.app.state.session_factory() as db:
            for number in range(1, versions + 1):
                db.add(
                    MasterProfile(
                        user_id=self.user_id,
                        version=number,
                        status="validated",
                        data=data.model_dump(mode="json"),
                        source="january",
                    )
                )
            await db.commit()

    async def profile_versions(self) -> list[MasterProfile]:
        async with self.app.state.session_factory() as db:
            stmt = select(MasterProfile).where(MasterProfile.user_id == self.user_id)
            return list((await db.execute(stmt.order_by(MasterProfile.version))).scalars())


def draft_results(*, to_check: Sequence[str] = ()) -> list[DraftResult]:
    """Les quatre brouillons d'un projet validé ; ceux de `to_check` sont « à vérifier »."""
    entry = ProfileEntryDraft(
        name=TITLE,
        description="Une API de suivi de lecture avec FastAPI.",
        achievements=["Trois routes documentées"],
    )
    texts: dict[Literal["cv_line", "profile_entry", "linkedin_post", "readme_plan"], str] = {
        "cv_line": "Construit une API de suivi de lecture.",
        "profile_entry": "\n".join([entry.name, entry.description, *entry.achievements]),
        "linkedin_post": "J'ai construit une API de suivi de lecture. " * 20,
        "readme_plan": "Installation\nUtilisation\nTests",
    }
    return [
        DraftResult(
            kind=kind,
            content=text,
            entry=entry if kind == "profile_entry" else None,
            status="to_check" if kind in to_check else "ready",
            flags=["kubernetes"] if kind in to_check else [],
        )
        for kind, text in texts.items()
    ]


def outcome(
    met: Sequence[bool] = (True, True, True, True),
    *,
    drafts: Sequence[DraftResult] | None = None,
    repo: Literal["read", "unreadable", "none"] = "read",
) -> ReviewOutcome:
    """L'issue d'une évaluation : un résultat par critère ; validée si tous sont atteints (avec
    les quatre brouillons), sinon à reprendre (sans brouillons)."""
    results = [
        CriterionResult(index=number, met=ok, comment=f"Commentaire {number}.")
        for number, ok in enumerate(met, start=1)
    ]
    validated = all(met)
    return ReviewOutcome(
        verdict="validated" if validated else "to_redo",
        results=results,
        feedback="Le retour du Praticien.",
        repo_status=repo,
        drafts=(list(drafts) if drafts is not None else draft_results()) if validated else None,
    )


Files = list[tuple[str, tuple[str, bytes, str]]]


def shots(*items: tuple[str, bytes]) -> Files:
    return [("screenshots", (name, data, "application/octet-stream")) for name, data in items]


async def submit(
    client: httpx.AsyncClient,
    project_id: str,
    data: dict[str, str] | None = None,
    files: Files | None = None,
) -> httpx.Response:
    return await client.post(
        f"{API}/{project_id}/submit", data=SUBMISSION if data is None else data, files=files
    )


def stored(tmp_path: Path, user_id: str) -> list[Path]:
    folder = tmp_path / "storage" / user_id / "projects"
    return sorted(folder.glob("*")) if folder.exists() else []
