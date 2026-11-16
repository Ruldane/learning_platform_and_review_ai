"""Fausse API de la partie `projets` du contrôle de la phase 8 : le Portfolio, un projet, le rendu
(multipart), la session d'évaluation, la carte des compétences et le profil maître, avec les
réponses que le vrai back rend. S'ajoute à `FakeApi` (réglages, radar, brief) pour la partie
`tout`. Aucun réseau."""

import copy
import json
from typing import Any

import httpx

from scripts.phase8_projects_rules import REPO_URL
from tests.scripts.phase8_support import FakeApi

TITLE = "Mini API de notes"
README_LINE = "Requests est une bibliothèque HTTP élégante et simple pour Python."
README_PATH = "/psf/requests/HEAD/README.md"
SKILLS = ("Flask", "Tests automatisés")
BRIEF: dict[str, Any] = {
    "title": TITLE,
    "context": "Tu écris une petite API pour ranger des notes personnelles.",
    "objective": "Livrer une API de notes testée, documentée en quelques lignes.",
    "constraints": ["Python 3.12 seulement", "Pas de base de données externe"],
    "criteria": [
        "Une route crée une note.",
        "Les tests passent.",
        "Le README explique le lancement.",
    ],
    "hours": 4,
    "deliverable": "either",
}
DRAFT_KINDS = ("cv_line", "profile_entry", "linkedin_post", "readme_plan")
ENTRY: dict[str, Any] = {
    "name": "API de notes",
    "description": "Une API de notes testée.",
    "achievements": [],
}


def project_json(project_id: str = "p1", status: str = "todo", **over: Any) -> dict[str, Any]:
    project = {
        "id": project_id,
        "module_id": f"m-{project_id}",
        "program_id": "g1",
        "title": f"{TITLE} {project_id}",
        "status": status,
        "brief": copy.deepcopy(BRIEF) if status not in ("brief_pending", "brief_failed") else None,
        "submissions": [],
        "evaluation": None,
        "drafts": [],
        "validated_at": None,
        "profile_version": None,
        "session_id": None,
        "week": 1,
        "rank": 1,
        "skills": list(SKILLS),
    }
    return project | over


def evaluation(met: list[bool], repo_status: str = "read") -> dict[str, Any]:
    results = [
        {"index": rank, "criterion": text, "met": ok, "comment": f"Commentaire du critère {rank}."}
        for rank, (text, ok) in enumerate(zip(BRIEF["criteria"], met, strict=True), 1)
    ]
    verdict = "validated" if all(met) else "to_redo"
    return {
        "at": "2026-11-16T10:00:00Z",
        "verdict": verdict,
        "results": results,
        "feedback": "Un retour écrit par le Praticien, assez long pour être cherché.",
        "repo_status": repo_status,
    }


def drafts(statuses: tuple[str, ...] = ("ready", "ready", "ready", "to_check")) -> list[Any]:
    found = []
    for kind, status in zip(DRAFT_KINDS, statuses, strict=True):
        entry = ENTRY if kind == "profile_entry" else None
        found.append(
            {"kind": kind, "status": status, "content": f"Brouillon {kind}.", "entry": entry}
            | {"flags": [], "edited": False}
        )
    return found


class ProjectsApi(FakeApi):
    """`outcome` : `validated` (4 brouillons), `no_drafts` (validé, brouillons indisponibles) ou
    `to_redo` (deux critères sur trois non atteints) ; `review_polls` : interrogations de la
    session avant qu'elle ne finisse."""

    def __init__(
        self,
        projects: list[dict[str, Any]] | None = None,
        *,
        outcome: str = "validated",
        repo_status: str = "read",
        review_polls: int = 2,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.projects = {
            p["id"]: p for p in (projects if projects is not None else [project_json()])
        }
        self.outcome, self.repo_status, self.review_polls = outcome, repo_status, review_polls
        self.profile_version = 3
        self.profile_projects: list[dict[str, Any]] = [{"name": "Ancien projet"}]
        self.level = "prouve"
        self.submit_form: bytes = b""
        self.submit_type = ""
        self.brief_posts: list[str] = []
        self.brief_polls = 0
        self.entries = 0
        self._review_ticks = 0
        self.pages[README_PATH] = f"# Requests\n\n{README_LINE}\n\n[badge](https://x.example)\n"

    # -- routes ---------------------------------------------------------------------------

    def _route(self, request: httpx.Request, path: str, method: str) -> Any:
        parts = path.strip("/").split("/")
        if parts[0] == "projects":
            return self._projects(request, parts[1:], method)
        if path == "/profile":
            return self._profile()
        if path == "/skills/graph":
            return {
                "nodes": [
                    {"id": f"k{n}", "name": s, "level": self.level, "evidence_count": 1}
                    for n, s in enumerate(SKILLS)
                ]
            }
        if path == "/sessions/s-proj":
            return self._session()
        return super()._route(request, path, method)

    def _projects(self, request: httpx.Request, parts: list[str], method: str) -> Any:
        if not parts:
            return [p | {"program_title": "Programme", "hours": 4} for p in self.projects.values()]
        project = self.projects[parts[0]]
        if len(parts) == 1:
            if project["status"] == "brief_pending":
                self._brief_tick(project)
            return project
        if parts[1] == "brief":
            self.brief_posts.append(parts[0])
            project["status"] = "brief_pending"
            return httpx.Response(202, json={"session_id": "s-brief-p"})
        if parts[1] == "submit":
            return self._submit(request, project)
        return self._entry(request, project)

    def _brief_tick(self, project: dict[str, Any]) -> None:
        self.brief_polls += 1
        if self.brief_polls > self.polls:
            project["status"], project["brief"] = "todo", copy.deepcopy(BRIEF)

    def _submit(self, request: httpx.Request, project: dict[str, Any]) -> httpx.Response:
        self.submit_type = request.headers["content-type"]
        self.submit_form = request.content
        text = request.content.decode()
        project["submissions"] = [
            {
                "at": "2026-11-16T10:00:00Z",
                "repo_url": REPO_URL,
                "description": text.split('name="description"\r\n\r\n')[1].split("\r\n--")[0],
                "screenshots": 0,
            }
        ]
        project["status"], project["session_id"] = "reviewing", "s-proj"
        return httpx.Response(202, json={"session_id": "s-proj"})

    def _session(self) -> dict[str, Any]:
        self._review_ticks += 1
        done = self._review_ticks > self.review_polls
        if done:
            self._finish()
        return {
            "status": "completed" if done else "running",
            "tokens_in": 4000,
            "tokens_out": 800,
            "cost_usd": 0.0042,
            "last_seq": 0,
        }

    def _finish(self) -> None:
        project = next((p for p in self.projects.values() if p["status"] == "reviewing"), None)
        if project is None:  # relue après la fin (coût, appels) : déjà rangée
            return
        met = [True, True, True] if self.outcome != "to_redo" else [True, False, False]
        project["evaluation"] = evaluation(met, self.repo_status)
        project["session_id"] = None
        if self.outcome == "to_redo":
            project["status"] = "to_redo"
            return
        project["status"] = "validated"
        project["drafts"] = [] if self.outcome == "no_drafts" else drafts()

    def _profile(self) -> dict[str, Any]:
        data = {"projects": self.profile_projects}
        return {"validated": {"version": self.profile_version, "data": data}, "draft": None}

    def _entry(self, request: httpx.Request, project: dict[str, Any]) -> Any:
        if project["profile_version"] is not None:
            return httpx.Response(409, json={"error": {"code": "entry_already_added"}})
        self.entries += 1
        self.profile_version += 1
        self.profile_projects.append({"name": json.loads(request.content)["name"]})
        project["profile_version"] = self.profile_version
        return project
